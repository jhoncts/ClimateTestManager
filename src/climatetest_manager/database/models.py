"""Modelos iniciais de persistência dos ensaios e da auditoria."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from climatetest_manager.database.base import Base
from climatetest_manager.domain.climate_rules import NORMATIVE_RULE_VERSION
from climatetest_manager.domain.enums import TestSituation


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
    situation: Mapped[str] = mapped_column(String(24), default=TestSituation.WAITING.value)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    normative_rule_version: Mapped[str] = mapped_column(String(40), default=NORMATIVE_RULE_VERSION)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    audit_events: Mapped[list[AuditEvent]] = relationship(
        back_populates="climate_test",
        cascade="all, delete-orphan",
    )


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
