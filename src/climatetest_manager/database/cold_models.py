"""Persistência adicional da v0.8.6 para acondicionamento e resistência térmica ao frio."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from climatetest_manager.database.base import Base


class ThermalColdWorkflowRecord(Base):
    """Estado opcional do fluxo pós-calor sem reinterpretar ensaios legados."""

    __tablename__ = "thermal_cold_workflows"

    climate_test_id: Mapped[int] = mapped_column(
        ForeignKey("climate_tests.id", ondelete="CASCADE"),
        primary_key=True,
    )
    cold_planned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    minimum_ambient_service_temperature_c: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )

    conditioning_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    conditioning_nominal_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    conditioning_maximum_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    conditioning_ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    cold_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cold_nominal_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cold_maximum_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cold_ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    cold_skipped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cold_skip_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="not_planned", nullable=False)
