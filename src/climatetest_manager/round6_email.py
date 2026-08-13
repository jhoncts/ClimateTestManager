"""Entrega imediata e diagnosticável de alertas de falha na R6."""

from __future__ import annotations

import asyncio

from climatetest_manager import app as legacy_app
from climatetest_manager import production_app
from climatetest_manager.config import load_email_settings
from climatetest_manager.services.notifications import (
    EmailNotificationProvider,
    deliver_pending_incident_emails,
)


def _incident_recipients(app) -> list[str]:
    """Notifica administradores e também quem acabou de registrar a falha."""

    values = list(app._auth_service.notification_admin_emails())
    reporter_email = str(getattr(app._current_user, "email", "") or "").strip()
    if reporter_email:
        values.append(reporter_email)
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        email = value.strip()
        key = email.casefold()
        if email and key not in seen:
            seen.add(key)
            unique.append(email)
    return unique


def _deliver_sync(app) -> tuple[str, int, int, int]:
    with legacy_app._INCIDENT_EMAIL_LOCK:
        settings = load_email_settings()
        if not settings.automatic_enabled:
            return "disabled", 0, 0, 0
        recipients = _incident_recipients(app)
        if not recipients:
            return "no_recipients", 0, 0, 0
        delivered, failed = deliver_pending_incident_emails(
            app._repository,
            EmailNotificationProvider(settings, recipients),
        )
        return "attempted", delivered, failed, len(recipients)


async def _deliver_incident_email_queue(self) -> None:
    try:
        status, delivered, failed, recipient_count = await asyncio.to_thread(_deliver_sync, self)
    except Exception as error:
        self._show_message(
            f"Falha registrada, mas o envio de e-mail falhou: {error}",
            error=True,
        )
        return

    if delivered:
        self._show_message(
            "Falha registrada. O aviso interno foi criado e o e-mail foi enviado "
            f"para {recipient_count} destinatário(s)."
        )
        return
    if failed:
        self._show_message(
            "Falha registrada e salva, porém o servidor SMTP recusou o e-mail. "
            "Use Configurações > E-mail para testar a conta; o envio continuará pendente.",
            error=True,
        )
        return
    if status == "disabled":
        self._show_message(
            "Falha registrada. O aviso interno foi criado, mas o e-mail automático está "
            "desativado ou sem host/remetente/usuário/senha completos.",
            error=True,
        )
        return
    if status == "no_recipients":
        self._show_message(
            "Falha registrada. Não existe e-mail válido no usuário atual nem em um "
            "administrador ativo para receber o alerta.",
            error=True,
        )


def install() -> None:
    production_app.ProductionClimateTestApplication._deliver_incident_email_queue = (
        _deliver_incident_email_queue
    )
