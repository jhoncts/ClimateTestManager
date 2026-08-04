"""Entrega idempotente dos avisos persistidos pelo fluxo operacional."""

import smtplib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Protocol

from climatetest_manager.config import EmailSettings, normalize_smtp_password
from climatetest_manager.repositories.climate_tests import ClimateTestRepository

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
        from windows_toasts import Toast, WindowsToaster

        toast = Toast()
        toast.text_fields = [title, message]
        WindowsToaster("ClimateTest Manager").show_toast(toast)


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
    now_provider: Callable[[], datetime] = datetime.now,
) -> tuple[int, int]:
    """Entrega cada canal uma única vez e devolve eventos completos e falhas."""

    delivered = 0
    failed = 0
    last_error: str | None = None
    now = now_provider().replace(microsecond=0)
    for event in repository.list_due_notifications(now):
        desktop_complete = event.desktop_sent_at is not None or provider is None
        email_complete = event.email_sent_at is not None or email_provider is None
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
