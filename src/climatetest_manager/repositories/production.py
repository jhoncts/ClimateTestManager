"""Extensões de persistência voltadas ao uso real multiusuário."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from climatetest_manager.database.models import (
    ClimateTestRecord,
    SecurityAuditEvent,
    SystemIncidentRecord,
    UserNotificationReadRecord,
)
from climatetest_manager.repositories.climate_tests import (
    ClimateTestRepository,
    UserNotificationSummary,
)

_DISMISS_PREFIX = "dismissed_"


class ProductionClimateTestRepository(ClimateTestRepository):
    """Adiciona guardas de idempotência e preferências sem alterar o contrato base."""

    def report_system_incident(
        self,
        *,
        reason_code: str = "other",
        category: str,
        severity: str,
        description: str,
        immediate_action: str,
        reported_by: str,
    ) -> int:
        """Evita criar a mesma falha repetidamente por clique duplo/retransmissão."""

        normalized_description = description.strip()
        normalized_action = immediate_action.strip()
        normalized_reporter = reported_by.strip()
        cutoff = datetime.now(UTC) - timedelta(seconds=45)
        with self._session_factory() as session:
            statement = (
                select(SystemIncidentRecord)
                .where(
                    SystemIncidentRecord.reason_code == reason_code,
                    SystemIncidentRecord.category == category,
                    SystemIncidentRecord.description == normalized_description,
                    SystemIncidentRecord.immediate_action == normalized_action,
                    SystemIncidentRecord.reported_by == normalized_reporter,
                    SystemIncidentRecord.reported_at >= cutoff,
                )
                .order_by(SystemIncidentRecord.id.desc())
            )
            existing = session.scalar(statement)
            if existing is not None:
                return existing.id
            record = SystemIncidentRecord(
                reason_code=reason_code,
                category=category,
                severity=severity,
                description=normalized_description,
                immediate_action=normalized_action,
                reported_by=normalized_reporter,
            )
            session.add(record)
            session.commit()
            return record.id

    def list_user_notifications(self, **kwargs) -> list[UserNotificationSummary]:
        notifications = super().list_user_notifications(**kwargs)
        user_id = int(kwargs["user_id"])
        with self._session_factory() as session:
            dismissed = {
                (record.source_kind.removeprefix(_DISMISS_PREFIX), record.source_id)
                for record in session.scalars(
                    select(UserNotificationReadRecord).where(
                        UserNotificationReadRecord.user_id == user_id,
                        UserNotificationReadRecord.source_kind.in_(
                            (f"{_DISMISS_PREFIX}operation", f"{_DISMISS_PREFIX}incident")
                        ),
                    )
                )
            }
        return [
            item for item in notifications if (item.source_kind, item.source_id) not in dismissed
        ]

    def dismiss_user_notification(
        self,
        *,
        user_id: int,
        source_kind: str,
        source_id: int,
    ) -> None:
        if source_kind not in {"operation", "incident"}:
            raise ValueError("Origem de notificação inválida.")
        dismissed_kind = f"{_DISMISS_PREFIX}{source_kind}"
        with self._session_factory() as session:
            statement = select(UserNotificationReadRecord.id).where(
                UserNotificationReadRecord.user_id == user_id,
                UserNotificationReadRecord.source_kind == dismissed_kind,
                UserNotificationReadRecord.source_id == source_id,
            )
            if session.scalar(statement) is not None:
                return
            session.add(
                UserNotificationReadRecord(
                    user_id=user_id,
                    source_kind=dismissed_kind,
                    source_id=source_id,
                )
            )
            session.commit()

    def dismiss_user_notifications(
        self,
        *,
        user_id: int,
        sources: list[tuple[str, int]],
    ) -> None:
        for source_kind, source_id in dict.fromkeys(sources):
            self.dismiss_user_notification(
                user_id=user_id,
                source_kind=source_kind,
                source_id=source_id,
            )

    def delete_test_as_administrator(
        self,
        test_id: int,
        *,
        actor_user_id: int,
        actor_label: str,
        reason: str,
    ) -> None:
        """Remove um ensaio da operação e preserva um tombstone na auditoria de segurança."""

        normalized_reason = reason.strip()
        if len(normalized_reason) < 10:
            raise ValueError("Informe um motivo de exclusão com pelo menos 10 caracteres.")
        with self._session_factory() as session:
            record = session.get(ClimateTestRecord, test_id)
            if record is None:
                raise LookupError(f"Ensaio #{test_id} não encontrado.")
            details = (
                f"Ensaio #{record.id}; processo={record.process_number}; cliente={record.client}; "
                f"produto={record.product}; situação={record.situation}; motivo={normalized_reason}"
            )
            session.add(
                SecurityAuditEvent(
                    actor_user_id=actor_user_id,
                    actor_label=actor_label,
                    action="climate_test_deleted_by_admin",
                    details=details,
                )
            )
            session.delete(record)
            session.commit()
