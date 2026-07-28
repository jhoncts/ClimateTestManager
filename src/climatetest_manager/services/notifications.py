"""Entrega idempotente dos avisos persistidos pelo fluxo operacional."""

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from climatetest_manager.repositories.climate_tests import ClimateTestRepository


class NotificationProvider(Protocol):
    """Contrato que permite trocar a notificação local por outros canais no futuro."""

    def send(self, title: str, message: str) -> None: ...


class WindowsToastProvider:
    """Notificação nativa do Windows 10/11."""

    def send(self, title: str, message: str) -> None:
        from windows_toasts import Toast, WindowsToaster

        toast = Toast()
        toast.text_fields = [title, message]
        WindowsToaster("ClimateTest Manager").show_toast(toast)


def deliver_due_notifications(
    repository: ClimateTestRepository,
    provider: NotificationProvider,
    *,
    now_provider: Callable[[], datetime] = datetime.now,
) -> tuple[int, int]:
    """Entrega avisos vencidos uma única vez e devolve sucessos e falhas."""

    delivered = 0
    failed = 0
    last_error: str | None = None
    now = now_provider().replace(microsecond=0)
    for event in repository.list_due_notifications(now):
        try:
            provider.send(event.title, event.message)
        except Exception as error:  # pragma: no cover - depende da integração do Windows
            failed += 1
            last_error = str(error)
            repository.mark_notification_sent(
                event.id,
                sent_at=None,
                error_message=last_error,
            )
        else:
            delivered += 1
            repository.mark_notification_sent(event.id, sent_at=now)
    repository.record_notification_check(
        checked_at=now,
        delivered_count=delivered,
        failed_count=failed,
        last_error=last_error,
    )
    return delivered, failed
