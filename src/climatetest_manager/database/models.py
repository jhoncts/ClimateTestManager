"""Modelos iniciais de persistência dos ensaios e da auditoria."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from climatetest_manager.database.base import Base
from climatetest_manager.domain.climate_rules import NORMATIVE_RULE_VERSION
from climatetest_manager.domain.enums import ConditionInputMode, TestSituation


def utc_now() -> datetime:
    """Fornece um instante UTC consciente de fuso para os registros."""

    return datetime.now(UTC)


class ClimateTestRecord(Base):
    """Fotografia persistida de um ensaio e da regra normativa utilizada."""

    __tablename__ = "climate_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    client: Mapped[str] = mapped_column(String(160), index=True)
    process_number: Mapped[str] = mapped_column(String(80), index=True)
    product: Mapped[str] = mapped_column(String(200))
    ex_marking: Mapped[str] = mapped_column(String(240))
    epl: Mapped[str] = mapped_column(String(2))
    tamb_max_c: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    delta_t_max_k: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    service_temperature_c: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    selected_option: Mapped[str | None] = mapped_column(String(1), nullable=True)
    sample_quantity: Mapped[int] = mapped_column(Integer, default=1)
    input_mode: Mapped[str] = mapped_column(
        String(24),
        default=ConditionInputMode.CALCULATED.value,
    )
    ts_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    situation: Mapped[str] = mapped_column(String(24), default=TestSituation.WAITING.value)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    normative_rule_version: Mapped[str] = mapped_column(String(40), default=NORMATIVE_RULE_VERSION)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    chamber_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    chamber_nominal_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    chamber_maximum_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    chamber_ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    drying_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    drying_nominal_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    drying_maximum_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    drying_ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    audit_events: Mapped[list[AuditEvent]] = relationship(
        back_populates="climate_test",
        cascade="all, delete-orphan",
    )
    condition_snapshot: Mapped[ClimateConditionSnapshot | None] = relationship(
        back_populates="climate_test",
        cascade="all, delete-orphan",
        uselist=False,
    )
    notifications: Mapped[list[NotificationEvent]] = relationship(
        back_populates="climate_test",
        cascade="all, delete-orphan",
    )
    pause_intervals: Mapped[list[ClimateTestPauseRecord]] = relationship(
        back_populates="climate_test",
        cascade="all, delete-orphan",
    )


class ClimateConditionSnapshot(Base):
    """Condição normativa imutável aplicada no momento do cadastro."""

    __tablename__ = "climate_condition_snapshots"

    climate_test_id: Mapped[int] = mapped_column(
        ForeignKey("climate_tests.id", ondelete="CASCADE"), primary_key=True
    )
    rule_id: Mapped[str] = mapped_column(String(40))
    normative_rule_version: Mapped[str] = mapped_column(String(40))
    option: Mapped[str] = mapped_column(String(1))
    service_temperature_c: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    chamber_temperature_c: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    chamber_temperature_tolerance_k: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    chamber_humidity_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    chamber_humidity_tolerance_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    chamber_duration_hours: Mapped[int] = mapped_column(Integer)
    chamber_duration_positive_tolerance_hours: Mapped[int] = mapped_column(Integer)
    drying_required: Mapped[bool] = mapped_column(Boolean)
    drying_temperature_c: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    drying_temperature_tolerance_k: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    drying_duration_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    drying_duration_positive_tolerance_hours: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    climate_test: Mapped[ClimateTestRecord] = relationship(back_populates="condition_snapshot")


class AuditEvent(Base):
    """Alteração relevante realizada em um ensaio."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    climate_test_id: Mapped[int] = mapped_column(
        ForeignKey("climate_tests.id", ondelete="CASCADE"), index=True
    )
    actor: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(80))
    field_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    climate_test: Mapped[ClimateTestRecord] = relationship(back_populates="audit_events")


class NotificationEvent(Base):
    """Aviso persistente para evitar duplicidade entre execuções em segundo plano."""

    __tablename__ = "notification_events"
    __table_args__ = (
        UniqueConstraint("climate_test_id", "event_key", name="uq_notification_test_event"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    climate_test_id: Mapped[int] = mapped_column(
        ForeignKey("climate_tests.id", ondelete="CASCADE"), index=True
    )
    event_key: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    scheduled_for_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    desktop_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    climate_test: Mapped[ClimateTestRecord] = relationship(back_populates="notifications")


class NotifierRunState(Base):
    """Última verificação realizada pelo agente de notificações."""

    __tablename__ = "notifier_run_state"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class ResourcePauseRecord(Base):
    """Período em que um equipamento ficou indisponível para o laboratório."""

    __tablename__ = "resource_pauses"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource: Mapped[str] = mapped_column(String(32), index=True)
    reason: Mapped[str] = mapped_column(Text)
    paused_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    affected_tests: Mapped[list[ClimateTestPauseRecord]] = relationship(
        back_populates="resource_pause",
        cascade="all, delete-orphan",
    )


class ClimateTestPauseRecord(Base):
    """Vincula uma parada do equipamento aos ensaios afetados naquele instante."""

    __tablename__ = "climate_test_pauses"
    __table_args__ = (
        UniqueConstraint(
            "climate_test_id",
            "resource_pause_id",
            name="uq_test_resource_pause",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    climate_test_id: Mapped[int] = mapped_column(
        ForeignKey("climate_tests.id", ondelete="CASCADE"),
        index=True,
    )
    resource_pause_id: Mapped[int] = mapped_column(
        ForeignKey("resource_pauses.id", ondelete="CASCADE"),
        index=True,
    )
    phase: Mapped[str] = mapped_column(String(32))
    paused_at: Mapped[datetime] = mapped_column(DateTime)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    climate_test: Mapped[ClimateTestRecord] = relationship(back_populates="pause_intervals")
    resource_pause: Mapped[ResourcePauseRecord] = relationship(back_populates="affected_tests")


class UserRecord(Base):
    """Conta local usada para autenticação e identificação das operações."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40))
    normalized_username: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254))
    normalized_email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(300))
    profile_photo_b64: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(24), default="operator")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    sessions: Mapped[list[UserSessionRecord]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserSessionRecord(Base):
    """Sessão local revogável; somente o resumo criptográfico do token é salvo."""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[UserRecord] = relationship(back_populates="sessions")


class SecurityAuditEvent(Base):
    """Trilha de segurança separada dos eventos técnicos de cada ensaio."""

    __tablename__ = "security_audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_label: Mapped[str] = mapped_column(String(180))
    action: Mapped[str] = mapped_column(String(100))
    target_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SystemIncidentRecord(Base):
    """Falha do sistema e tratamento adotado, preservados para auditoria."""

    __tablename__ = "system_incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    reason_code: Mapped[str] = mapped_column(String(80), default="other", index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(24), index=True)
    description: Mapped[str] = mapped_column(Text)
    immediate_action: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    reported_by: Mapped[str] = mapped_column(String(180))
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    corrective_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(180), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    admin_email_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class UserNotificationReadRecord(Base):
    """Marca, por usuário, quais avisos da central interna já foram lidos."""

    __tablename__ = "user_notification_reads"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source_kind",
            "source_id",
            name="uq_user_notification_source",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    source_kind: Mapped[str] = mapped_column(String(24), index=True)
    source_id: Mapped[int] = mapped_column(Integer, index=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AdministratorRecoveryRecord(Base):
    """Hash do código que permite recuperar o administrador apenas no servidor."""

    __tablename__ = "administrator_recovery"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    code_hash: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
