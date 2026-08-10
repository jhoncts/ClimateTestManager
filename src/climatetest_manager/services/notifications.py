"""Entrega idempotente dos avisos persistidos pelo fluxo operacional."""

import smtplib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from html import escape
from typing import Protocol

from climatetest_manager.config import EmailSettings, normalize_smtp_password
from climatetest_manager.repositories.climate_tests import ClimateTestRepository
from climatetest_manager.services.branding import brand_logo_path

SMTP_LOCAL_HOSTNAME = "[127.0.0.1]"


@dataclass(frozen=True, slots=True)
class EmailDeliveryReceipt:
    """Comprovante local de que o servidor SMTP aceitou a mensagem."""

    recipients: tuple[str, ...]
    message_id: str


class NotificationProvider(Protocol):
    """Contrato que permite trocar a notificação local por outros canais no futuro."""

    def send(self, title: str, message: str) -> object | None: ...


class WindowsToastProvider:
    """Notificação nativa do Windows 10/11."""

    def send(self, title: str, message: str) -> None:
        from windows_toasts import (
            InteractableWindowsToaster,
            Toast,
            ToastDisplayImage,
            ToastImagePosition,
        )

        toast = Toast()
        compact_lines = [line.strip() for line in message.splitlines() if line.strip()]
        compact_message = " • ".join(compact_lines[:4])
        toast.text_fields = [title, compact_message]
        logo_path = brand_logo_path()
        if logo_path.exists():
            toast.AddImage(
                ToastDisplayImage.fromPath(
                    str(logo_path),
                    altText="ClimateTest Manager",
                    position=ToastImagePosition.AppLogo,
                )
            )
        InteractableWindowsToaster("ClimateTest Manager").show_toast(toast)


def _email_accent(title: str) -> tuple[str, str]:
    normalized = title.casefold()
    if "falha" in normalized or "ultrapass" in normalized or "atras" in normalized:
        return "#DC2626", "Ação necessária"
    if "2 horas" in normalized or "amanhã" in normalized or "amanha" in normalized:
        return "#D97706", "Atenção ao prazo"
    return "#087E8B", "Atualização operacional"


def _email_html(title: str, message: str, *, logo_cid: str | None = None) -> str:
    """Monta HTML compatível com clientes de e-mail sem depender de CSS externo."""

    accent, eyebrow = _email_accent(title)
    rows: list[str] = []
    paragraphs: list[str] = []
    for raw_line in message.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" in line:
            label, value = line.split(":", maxsplit=1)
            if label.strip() and value.strip():
                rows.append(
                    "<tr>"
                    f'<td style="padding:8px 12px;color:#64748B;font-size:13px;'
                    f'width:34%;border-bottom:1px solid #E2E8F0;">{escape(label.strip())}</td>'
                    f'<td style="padding:8px 12px;color:#0F172A;font-size:13px;'
                    f'font-weight:600;border-bottom:1px solid #E2E8F0;">'
                    f"{escape(value.strip())}</td></tr>"
                )
                continue
        paragraphs.append(
            f'<p style="margin:0 0 8px;color:#334155;font-size:14px;line-height:1.55;">'
            f"{escape(line)}</p>"
        )
    detail_table = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="margin-top:16px;border:1px solid #E2E8F0;border-radius:12px;'
        'border-collapse:separate;overflow:hidden;">' + "".join(rows) + "</table>"
        if rows
        else ""
    )
    logo = (
        f'<img src="cid:{escape(logo_cid)}" width="48" height="48" '
        'alt="ClimateTest Manager" style="display:block;border:0;border-radius:12px;">'
        if logo_cid
        else "C"
    )
    return f"""<!doctype html>
<html lang="pt-BR"><body style="margin:0;background:#F1F5F9;font-family:Segoe UI,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:28px 12px;">
<tr><td align="center">
<table role="presentation" width="620" cellpadding="0" cellspacing="0"
 style="max-width:620px;background:#FFFFFF;border-radius:18px;overflow:hidden;
 box-shadow:0 12px 36px rgba(15,23,42,.10);">
<tr><td style="padding:22px 26px;background:linear-gradient(135deg,#102A43,#087E8B);">
<table role="presentation" cellpadding="0" cellspacing="0"><tr>
<td style="width:48px;height:48px;border-radius:14px;background:#FFFFFF;text-align:center;
color:#087E8B;font-size:26px;font-weight:800;">{logo}</td>
<td style="padding-left:14px;color:#FFFFFF;"><div style="font-size:18px;font-weight:700;">
ClimateTest Manager</div><div style="font-size:12px;color:#BAE6FD;margin-top:3px;">
Controle de ensaios laboratoriais</div></td></tr></table></td></tr>
<tr><td style="height:5px;background:{accent};font-size:0;">&nbsp;</td></tr>
<tr><td style="padding:28px 30px 24px;">
<div style="color:{accent};font-size:11px;letter-spacing:1.2px;text-transform:uppercase;
font-weight:700;margin-bottom:8px;">{eyebrow}</div>
<h1 style="margin:0 0 18px;color:#0F172A;font-size:22px;line-height:1.3;">
{escape(title)}</h1>
{"".join(paragraphs)}{detail_table}
<div style="margin-top:24px;padding:13px 15px;border-radius:10px;background:#F8FAFC;
color:#64748B;font-size:12px;line-height:1.5;">Mensagem automática e auditável do
ClimateTest Manager. Acesse a central de notificações para consultar o histórico.</div>
</td></tr><tr><td style="padding:16px 30px;background:#F8FAFC;color:#94A3B8;font-size:11px;">
ClimateTest Manager • Desenvolvido por Jhon Cleiton</td></tr></table>
</td></tr></table></body></html>"""


class EmailNotificationProvider:
    """Envia o mesmo aviso aos e-mails de todas as contas ativas."""

    def __init__(self, settings: EmailSettings, recipients: list[str]) -> None:
        if not settings.is_configured:
            raise ValueError("A configuração de e-mail está incompleta.")
        normalized_recipients = tuple(
            dict.fromkeys(recipient.strip() for recipient in recipients if recipient.strip())
        )
        if not normalized_recipients:
            raise ValueError("Não há usuários ativos com e-mail cadastrado.")
        self._settings = settings
        self._recipients = normalized_recipients

    def send(self, title: str, message: str) -> EmailDeliveryReceipt:
        username = self._settings.username.strip()
        password = normalize_smtp_password(self._settings.host, self._settings.password)
        try:
            username.encode("ascii")
            password.encode("ascii")
        except UnicodeEncodeError as error:
            raise ValueError(
                "O usuário ou a senha SMTP contém acento ou caractere inválido. "
                "Informe novamente a senha de app."
            ) from error

        email = EmailMessage()
        email["Subject"] = f"[ClimateTest Manager] {title}"
        sender = self._settings.sender.strip()
        email["From"] = sender
        email["To"] = ", ".join(self._recipients)
        email["Date"] = formatdate(localtime=True)
        email["Message-ID"] = make_msgid(domain="climatetest.local")
        email.set_content(
            f"{message}\n\nEste aviso foi enviado automaticamente pelo ClimateTest Manager."
        )
        logo_path = brand_logo_path()
        logo_cid = make_msgid(domain="climatetest.local") if logo_path.exists() else None
        email.add_alternative(
            _email_html(
                title,
                message,
                logo_cid=logo_cid[1:-1] if logo_cid else None,
            ),
            subtype="html",
        )
        if logo_cid:
            html_part = email.get_payload()[-1]
            html_part.add_related(
                logo_path.read_bytes(),
                maintype="image",
                subtype="png",
                cid=logo_cid,
                filename="climatetest-logo.png",
                disposition="inline",
            )
        try:
            with smtplib.SMTP(
                self._settings.host,
                self._settings.port,
                local_hostname=SMTP_LOCAL_HOSTNAME,
                timeout=20,
            ) as client:
                client.ehlo()
                if self._settings.use_tls:
                    client.starttls()
                    client.ehlo()
                client.login(username, password)
                refused = client.send_message(
                    email,
                    from_addr=sender,
                    to_addrs=list(self._recipients),
                )
        except smtplib.SMTPAuthenticationError as error:
            provider = (
                "O Gmail" if self._settings.host.casefold() == "smtp.gmail.com" else "O servidor"
            )
            raise RuntimeError(
                f"{provider} recusou a autenticação. "
                "Confira o usuário e gere uma nova senha de app."
            ) from error
        except smtplib.SMTPRecipientsRefused as error:
            recipients = ", ".join(error.recipients)
            raise RuntimeError(
                f"O servidor recusou todos os destinatários: {recipients}."
            ) from error
        except smtplib.SMTPSenderRefused as error:
            raise RuntimeError(
                f"O servidor recusou o remetente {sender}. Confira a conta configurada."
            ) from error
        except smtplib.SMTPDataError as error:
            raise RuntimeError(
                f"O servidor não aceitou o conteúdo da mensagem (código {error.smtp_code})."
            ) from error
        if refused:
            refused_addresses = ", ".join(refused)
            raise RuntimeError(f"O servidor recusou estes destinatários: {refused_addresses}.")
        return EmailDeliveryReceipt(
            recipients=self._recipients,
            message_id=str(email["Message-ID"]),
        )


def deliver_due_notifications(
    repository: ClimateTestRepository,
    provider: NotificationProvider | None,
    *,
    email_provider: NotificationProvider | None = None,
    require_desktop: bool | None = None,
    require_email: bool | None = None,
    now_provider: Callable[[], datetime] = datetime.now,
) -> tuple[int, int]:
    """Entrega cada canal uma única vez e devolve eventos completos e falhas."""

    delivered = 0
    failed = 0
    last_error: str | None = None
    now = now_provider().replace(microsecond=0)
    desktop_required = provider is not None if require_desktop is None else require_desktop
    email_required = email_provider is not None if require_email is None else require_email
    for event in repository.list_due_notifications(now):
        desktop_complete = event.desktop_sent_at is not None or not desktop_required
        email_complete = event.email_sent_at is not None or not email_required
        if not desktop_complete and provider is not None:
            try:
                provider.send(event.title, event.message)
            except Exception as error:  # pragma: no cover - integração do Windows
                failed += 1
                last_error = f"Aviso do Windows: {error}"
            else:
                desktop_complete = True
                repository.mark_notification_channel_sent(
                    event.id,
                    channel="desktop",
                    sent_at=now,
                )
        if not email_complete and email_provider is not None:
            try:
                email_provider.send(event.title, event.message)
            except Exception as error:  # pragma: no cover - depende do servidor SMTP
                failed += 1
                last_error = f"E-mail: {error}"
            else:
                email_complete = True
                repository.mark_notification_channel_sent(
                    event.id,
                    channel="email",
                    sent_at=now,
                )
        if desktop_complete and email_complete:
            delivered += 1
            repository.mark_notification_sent(event.id, sent_at=now)
        else:
            repository.mark_notification_sent(
                event.id,
                sent_at=None,
                error_message=last_error,
            )
    repository.record_notification_check(
        checked_at=now,
        delivered_count=delivered,
        failed_count=failed,
        last_error=last_error,
    )
    return delivered, failed


def deliver_pending_incident_emails(
    repository: ClimateTestRepository,
    email_provider: NotificationProvider | None,
    *,
    now_provider: Callable[[], datetime] = datetime.now,
) -> tuple[int, int]:
    """Envia falhas somente aos administradores e mantém a fila para nova tentativa."""

    if email_provider is None:
        return 0, 0
    delivered = 0
    failed = 0
    now = now_provider().replace(microsecond=0)
    for incident in repository.list_pending_incident_emails():
        title = f"Falha #{incident.id} registrada • Prioridade {incident.severity}"
        message = "\n".join(
            (
                f"Categoria: {incident.category}",
                f"Prioridade: {incident.severity}",
                f"Registrada por: {incident.reported_by}",
                f"Data do registro: {incident.reported_at:%d/%m/%Y %H:%M}",
                f"Ocorrido: {incident.description}",
                f"Ação tomada: {incident.immediate_action}",
            )
        )
        try:
            email_provider.send(title, message)
        except Exception as error:  # pragma: no cover - depende do servidor SMTP
            failed += 1
            repository.mark_incident_email(
                incident.id,
                sent_at=None,
                error_message=str(error),
            )
        else:
            delivered += 1
            repository.mark_incident_email(incident.id, sent_at=now)
    return delivered, failed
