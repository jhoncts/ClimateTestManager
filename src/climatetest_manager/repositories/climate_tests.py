"""Persistência dos ensaios climáticos com SQLAlchemy."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, joinedload, selectinload, sessionmaker

from climatetest_manager.database.models import (
    AuditEvent,
    ClimateTestPauseRecord,
    ClimateTestRecord,
    NotificationEvent,
    NotifierRunState,
    ResourcePauseRecord,
    SystemIncidentRecord,
    UserNotificationReadRecord,
)
from climatetest_manager.domain.enums import EquipmentResource, TestSituation


@dataclass(frozen=True, slots=True)
class RecentClimateTest:
    """Dados mínimos de um ensaio recente apresentados no dashboard."""

    id: int
    client: str
    process_number: str
    product: str
    epl: str
    service_temperature_c: str
    ts_reference: str | None
    input_mode: str
    selected_option: str
    sample_quantity: int
    situation: str
    chamber_temperature_c: str
    chamber_humidity_percent: str
    chamber_duration_hours: int


@dataclass(frozen=True, slots=True)
class DueNotification:
    """Aviso vencido pronto para ser entregue pelo agente em segundo plano."""

    id: int
    title: str
    message: str
    desktop_sent_at: datetime | None = None
    email_sent_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AuditHistoryEntry:
    """Evento associado ao ensaio para a consulta global de histórico."""

    test_id: int
    client: str
    process_number: str
    action: str
    actor: str
    occurred_at: datetime
    new_value: str | None
    reason: str | None


@dataclass(frozen=True, slots=True)
class NotificationStatus:
    """Resumo da última execução do agente local."""

    last_checked_at: datetime | None = None
    delivered_count: int = 0
    failed_count: int = 0
    last_error: str | None = None


@dataclass(frozen=True, slots=True)
class ResourcePauseState:
    """Estado desacoplado da sessão para os controles globais do equipamento."""

    resource: str
    paused_at: datetime
    reason: str
    affected_count: int


@dataclass(frozen=True, slots=True)
class SystemIncidentSummary:
    """Falha do sistema pronta para consulta sem expor o modelo persistente."""

    id: int
    category: str
    severity: str
    description: str
    immediate_action: str
    status: str
    reported_by: str
    reported_at: datetime
    corrective_action: str | None
    resolved_by: str | None
    resolved_at: datetime | None
    reason_code: str = "other"


@dataclass(frozen=True, slots=True)
class UserNotificationSummary:
    """Aviso operacional ou administrativo exibido na central interna."""

    source_kind: str
    source_id: int
    title: str
    message: str
    severity: str
    created_at: datetime
    is_read: bool


@dataclass(frozen=True, slots=True)
class PendingIncidentEmail:
    """Falha aguardando o alerta restrito por e-mail aos administradores."""

    id: int
    category: str
    severity: str
    description: str
    immediate_action: str
    reported_by: str
    reported_at: datetime


class ClimateTestRepository:
    """Isola o restante da aplicação dos detalhes de sessão do banco."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, climate_test: ClimateTestRecord) -> int:
        """Persiste um ensaio completo em uma única transação."""

        with self._session_factory() as session:
            session.add(climate_test)
            session.commit()
            return climate_test.id

    def count_by_situations(self, *situations: TestSituation) -> int:
        """Conta ensaios que estejam em qualquer uma das situações recebidas."""

        values = [situation.value for situation in situations]
        with self._session_factory() as session:
            statement = select(func.count(ClimateTestRecord.id)).where(
                ClimateTestRecord.situation.in_(values)
            )
            return session.scalar(statement) or 0

    def list_recent(self, *, limit: int = 6) -> list[RecentClimateTest]:
        """Retorna os cadastros mais recentes sem expor objetos de sessão à UI."""

        with self._session_factory() as session:
            statement = (
                select(ClimateTestRecord)
                .options(joinedload(ClimateTestRecord.condition_snapshot))
                .order_by(ClimateTestRecord.created_at.desc(), ClimateTestRecord.id.desc())
                .limit(limit)
            )
            records = session.scalars(statement).all()

            return [
                RecentClimateTest(
                    id=record.id,
                    client=record.client,
                    process_number=record.process_number,
                    product=record.product,
                    epl=record.epl,
                    service_temperature_c=str(record.service_temperature_c),
                    ts_reference=record.ts_reference,
                    input_mode=record.input_mode,
                    selected_option=record.selected_option or "-",
                    sample_quantity=record.sample_quantity,
                    situation=record.situation,
                    chamber_temperature_c=str(record.condition_snapshot.chamber_temperature_c),
                    chamber_humidity_percent=str(
                        record.condition_snapshot.chamber_humidity_percent
                    ),
                    chamber_duration_hours=record.condition_snapshot.chamber_duration_hours,
                )
                for record in records
                if record.condition_snapshot is not None
            ]

    def list_records(self) -> list[ClimateTestRecord]:
        """Retorna ensaios com a fotografia normativa para os casos de uso."""

        with self._session_factory() as session:
            statement = (
                select(ClimateTestRecord)
                .options(
                    joinedload(ClimateTestRecord.condition_snapshot),
                    selectinload(ClimateTestRecord.pause_intervals).joinedload(
                        ClimateTestPauseRecord.resource_pause
                    ),
                )
                .order_by(ClimateTestRecord.created_at.desc(), ClimateTestRecord.id.desc())
            )
            return list(session.scalars(statement).unique().all())

    def get(self, test_id: int) -> ClimateTestRecord | None:
        """Carrega um ensaio completo para a tela de detalhes."""

        with self._session_factory() as session:
            statement = (
                select(ClimateTestRecord)
                .where(ClimateTestRecord.id == test_id)
                .options(
                    joinedload(ClimateTestRecord.condition_snapshot),
                    selectinload(ClimateTestRecord.audit_events),
                    selectinload(ClimateTestRecord.notifications),
                    selectinload(ClimateTestRecord.pause_intervals).joinedload(
                        ClimateTestPauseRecord.resource_pause
                    ),
                )
            )
            return session.scalar(statement)

    def mutate(
        self,
        test_id: int,
        operation: Callable[[ClimateTestRecord], None],
    ) -> None:
        """Executa uma mudança de estado em uma única transação."""

        with self._session_factory() as session:
            statement = (
                select(ClimateTestRecord)
                .where(ClimateTestRecord.id == test_id)
                .options(
                    joinedload(ClimateTestRecord.condition_snapshot),
                    selectinload(ClimateTestRecord.audit_events),
                    selectinload(ClimateTestRecord.notifications),
                    selectinload(ClimateTestRecord.pause_intervals).joinedload(
                        ClimateTestPauseRecord.resource_pause
                    ),
                )
            )
            record = session.scalar(statement)
            if record is None:
                raise LookupError(f"Ensaio #{test_id} não encontrado.")
            operation(record)
            session.commit()

    def get_active_resource_pause(
        self,
        resource: EquipmentResource,
    ) -> ResourcePauseState | None:
        """Retorna a parada aberta do recurso, se houver."""

        with self._session_factory() as session:
            statement = (
                select(ResourcePauseRecord)
                .where(
                    ResourcePauseRecord.resource == resource.value,
                    ResourcePauseRecord.resumed_at.is_(None),
                )
                .options(selectinload(ResourcePauseRecord.affected_tests))
                .order_by(ResourcePauseRecord.paused_at.desc(), ResourcePauseRecord.id.desc())
            )
            record = session.scalar(statement)
            if record is None:
                return None
            return ResourcePauseState(
                resource=record.resource,
                paused_at=record.paused_at,
                reason=record.reason,
                affected_count=len(record.affected_tests),
            )

    def mutate_resource_state(
        self,
        resource: EquipmentResource,
        active_situation: TestSituation,
        operation: Callable[
            [Session, ResourcePauseRecord | None, list[ClimateTestRecord]],
            None,
        ],
    ) -> None:
        """Altera equipamento e ensaios atingidos em uma única transação."""

        with self._session_factory() as session:
            pause_statement = (
                select(ResourcePauseRecord)
                .where(
                    ResourcePauseRecord.resource == resource.value,
                    ResourcePauseRecord.resumed_at.is_(None),
                )
                .options(selectinload(ResourcePauseRecord.affected_tests))
                .order_by(ResourcePauseRecord.paused_at.desc(), ResourcePauseRecord.id.desc())
            )
            active_pause = session.scalar(pause_statement)
            records_statement = (
                select(ClimateTestRecord)
                .where(ClimateTestRecord.situation == active_situation.value)
                .options(
                    joinedload(ClimateTestRecord.condition_snapshot),
                    selectinload(ClimateTestRecord.audit_events),
                    selectinload(ClimateTestRecord.notifications),
                    selectinload(ClimateTestRecord.pause_intervals).joinedload(
                        ClimateTestPauseRecord.resource_pause
                    ),
                )
            )
            records = list(session.scalars(records_statement).unique().all())
            operation(session, active_pause, records)
            session.commit()

    def delete(self, test_id: int) -> None:
        """Exclui um cadastro ainda não iniciado em uma única transação."""

        with self._session_factory() as session:
            record = session.get(ClimateTestRecord, test_id)
            if record is None:
                raise LookupError(f"Ensaio #{test_id} não encontrado.")
            session.delete(record)
            session.commit()

    def list_due_notifications(self, now: datetime) -> list[DueNotification]:
        """Lista avisos ainda não entregues cujo horário já chegou."""

        with self._session_factory() as session:
            active_test_pause = exists(
                select(ClimateTestPauseRecord.id).where(
                    ClimateTestPauseRecord.climate_test_id == NotificationEvent.climate_test_id,
                    ClimateTestPauseRecord.resumed_at.is_(None),
                )
            )
            statement = (
                select(NotificationEvent)
                .where(
                    NotificationEvent.sent_at.is_(None),
                    NotificationEvent.scheduled_for_at <= now,
                    ~active_test_pause,
                )
                .order_by(NotificationEvent.scheduled_for_at, NotificationEvent.id)
            )
            return [
                DueNotification(
                    item.id,
                    item.title,
                    item.message,
                    item.desktop_sent_at,
                    item.email_sent_at,
                )
                for item in session.scalars(statement)
            ]

    def mark_notification_channel_sent(
        self,
        notification_id: int,
        *,
        channel: str,
        sent_at: datetime,
    ) -> None:
        """Marca um canal sem provocar repetição do outro em uma nova tentativa."""

        with self._session_factory() as session:
            event = session.get(NotificationEvent, notification_id)
            if event is None:
                return
            if channel == "desktop":
                event.desktop_sent_at = sent_at
            elif channel == "email":
                event.email_sent_at = sent_at
            else:
                raise ValueError("Canal de notificação inválido.")
            event.error_message = None
            session.commit()

    def mark_notification_sent(
        self,
        notification_id: int,
        *,
        sent_at: datetime | None,
        error_message: str | None = None,
    ) -> None:
        """Registra o resultado da tentativa de entrega."""

        with self._session_factory() as session:
            event = session.get(NotificationEvent, notification_id)
            if event is None:
                return
            event.sent_at = sent_at
            if sent_at is not None and event.desktop_sent_at is None:
                event.desktop_sent_at = sent_at
            event.error_message = error_message
            session.commit()

    def record_notification_check(
        self,
        *,
        checked_at: datetime,
        delivered_count: int,
        failed_count: int,
        last_error: str | None,
    ) -> None:
        """Persiste um diagnóstico pequeno para a tela de configurações."""

        with self._session_factory() as session:
            state = session.get(NotifierRunState, 1)
            if state is None:
                state = NotifierRunState(id=1)
                session.add(state)
            state.last_checked_at = checked_at
            state.delivered_count = delivered_count
            state.failed_count = failed_count
            state.last_error = last_error
            session.commit()

    def get_notification_status(self) -> NotificationStatus:
        """Retorna o resultado mais recente sem expor o modelo de banco."""

        with self._session_factory() as session:
            state = session.get(NotifierRunState, 1)
            if state is None:
                return NotificationStatus()
            return NotificationStatus(
                last_checked_at=state.last_checked_at,
                delivered_count=state.delivered_count,
                failed_count=state.failed_count,
                last_error=state.last_error,
            )

    def list_audit_history(self) -> list[AuditHistoryEntry]:
        """Lista todos os eventos com identificação do respectivo ensaio."""

        with self._session_factory() as session:
            statement = (
                select(AuditEvent, ClimateTestRecord)
                .join(ClimateTestRecord, AuditEvent.climate_test_id == ClimateTestRecord.id)
                .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
            )
            return [
                AuditHistoryEntry(
                    test_id=record.id,
                    client=record.client,
                    process_number=record.process_number,
                    action=event.action,
                    actor=event.actor,
                    occurred_at=event.occurred_at,
                    new_value=event.new_value,
                    reason=event.reason,
                )
                for event, record in session.execute(statement)
            ]

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
        """Registra a falha e a contenção inicial sem alterar registros anteriores."""

        record = SystemIncidentRecord(
            reason_code=reason_code,
            category=category,
            severity=severity,
            description=description,
            immediate_action=immediate_action,
            reported_by=reported_by,
        )
        with self._session_factory() as session:
            session.add(record)
            session.commit()
            return record.id

    def list_pending_incident_emails(self, *, limit: int = 20) -> list[PendingIncidentEmail]:
        """Retorna alertas de falha ainda não aceitos pelo servidor SMTP."""

        with self._session_factory() as session:
            statement = (
                select(SystemIncidentRecord)
                .where(SystemIncidentRecord.admin_email_sent_at.is_(None))
                .order_by(SystemIncidentRecord.reported_at, SystemIncidentRecord.id)
                .limit(limit)
            )
            return [
                PendingIncidentEmail(
                    id=record.id,
                    category=record.category,
                    severity=record.severity,
                    description=record.description,
                    immediate_action=record.immediate_action,
                    reported_by=record.reported_by,
                    reported_at=record.reported_at,
                )
                for record in session.scalars(statement)
            ]

    def mark_incident_email(
        self,
        incident_id: int,
        *,
        sent_at: datetime | None,
        error_message: str | None = None,
    ) -> None:
        with self._session_factory() as session:
            record = session.get(SystemIncidentRecord, incident_id)
            if record is None:
                raise LookupError(f"Falha do sistema #{incident_id} não encontrada.")
            record.admin_email_sent_at = sent_at
            record.admin_email_error = error_message
            session.commit()

    def resolve_system_incident(
        self,
        incident_id: int,
        *,
        corrective_action: str,
        resolved_by: str,
        resolved_at: datetime | None = None,
    ) -> None:
        """Encerra uma falha mantendo a descrição e a ação imediata originais."""

        with self._session_factory() as session:
            record = session.get(SystemIncidentRecord, incident_id)
            if record is None:
                raise LookupError(f"Falha do sistema #{incident_id} não encontrada.")
            if record.status == "resolved":
                raise ValueError("Esta falha já foi encerrada.")
            record.status = "resolved"
            record.corrective_action = corrective_action
            record.resolved_by = resolved_by
            record.resolved_at = resolved_at or datetime.now(UTC)
            session.commit()

    def list_system_incidents(self, *, limit: int = 20) -> list[SystemIncidentSummary]:
        """Lista primeiro as falhas abertas e depois as mais recentes."""

        with self._session_factory() as session:
            statement = (
                select(SystemIncidentRecord)
                .order_by(
                    (SystemIncidentRecord.status == "resolved").asc(),
                    SystemIncidentRecord.reported_at.desc(),
                    SystemIncidentRecord.id.desc(),
                )
                .limit(limit)
            )
            return [
                SystemIncidentSummary(
                    id=record.id,
                    reason_code=record.reason_code,
                    category=record.category,
                    severity=record.severity,
                    description=record.description,
                    immediate_action=record.immediate_action,
                    status=record.status,
                    reported_by=record.reported_by,
                    reported_at=record.reported_at,
                    corrective_action=record.corrective_action,
                    resolved_by=record.resolved_by,
                    resolved_at=record.resolved_at,
                )
                for record in session.scalars(statement)
            ]

    def list_user_notifications(
        self,
        *,
        user_id: int,
        is_admin: bool,
        now: datetime | None = None,
        limit: int = 80,
    ) -> list[UserNotificationSummary]:
        """Combina avisos operacionais e, para admins, falhas registradas."""

        current_time = (now or datetime.now()).replace(microsecond=0)
        with self._session_factory() as session:
            reads = {
                (record.source_kind, record.source_id)
                for record in session.scalars(
                    select(UserNotificationReadRecord).where(
                        UserNotificationReadRecord.user_id == user_id
                    )
                )
            }
            operational = session.scalars(
                select(NotificationEvent)
                .where(NotificationEvent.scheduled_for_at <= current_time)
                .order_by(NotificationEvent.scheduled_for_at.desc(), NotificationEvent.id.desc())
                .limit(limit)
            ).all()
            notifications = [
                UserNotificationSummary(
                    source_kind="operation",
                    source_id=record.id,
                    title=record.title,
                    message=record.message,
                    severity=(
                        "high"
                        if "ultrapassado" in record.title.casefold()
                        or "atras" in record.title.casefold()
                        else "info"
                    ),
                    created_at=record.scheduled_for_at,
                    is_read=("operation", record.id) in reads,
                )
                for record in operational
            ]
            if is_admin:
                incidents = session.scalars(
                    select(SystemIncidentRecord)
                    .order_by(
                        SystemIncidentRecord.reported_at.desc(),
                        SystemIncidentRecord.id.desc(),
                    )
                    .limit(limit)
                ).all()
                notifications.extend(
                    UserNotificationSummary(
                        source_kind="incident",
                        source_id=record.id,
                        title=f"Falha #{record.id} • Prioridade {record.severity}",
                        message=(
                            f"{record.category}\nRegistrada por {record.reported_by}\n"
                            f"{record.description}"
                        ),
                        severity=record.severity.casefold(),
                        created_at=record.reported_at,
                        is_read=("incident", record.id) in reads,
                    )
                    for record in incidents
                )
            return sorted(
                notifications,
                key=lambda item: item.created_at,
                reverse=True,
            )[:limit]

    def mark_user_notification_read(
        self,
        *,
        user_id: int,
        source_kind: str,
        source_id: int,
    ) -> None:
        if source_kind not in {"operation", "incident"}:
            raise ValueError("Origem de notificação inválida.")
        with self._session_factory() as session:
            exists_statement = select(UserNotificationReadRecord.id).where(
                UserNotificationReadRecord.user_id == user_id,
                UserNotificationReadRecord.source_kind == source_kind,
                UserNotificationReadRecord.source_id == source_id,
            )
            if session.scalar(exists_statement) is None:
                session.add(
                    UserNotificationReadRecord(
                        user_id=user_id,
                        source_kind=source_kind,
                        source_id=source_id,
                    )
                )
                session.commit()
