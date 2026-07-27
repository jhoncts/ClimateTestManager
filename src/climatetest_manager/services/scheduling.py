"""Cálculo de horários nominais e máximos das etapas."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from climatetest_manager.domain.climate_rules import PhaseCondition
from climatetest_manager.domain.enums import DeadlineCondition


@dataclass(frozen=True, slots=True)
class PhaseSchedule:
    """Prazos calculados a partir do início real de uma etapa."""

    started_at: datetime
    nominal_end_at: datetime
    maximum_end_at: datetime


def schedule_phase(started_at: datetime, condition: PhaseCondition) -> PhaseSchedule:
    """Calcula as saídas nominal e máxima sem alterar o instante informado."""

    return PhaseSchedule(
        started_at=started_at,
        nominal_end_at=started_at + timedelta(hours=condition.duration_hours),
        maximum_end_at=started_at + timedelta(hours=condition.maximum_duration_hours),
    )


def classify_deadline(
    now: datetime,
    nominal_end_at: datetime,
    maximum_end_at: datetime,
) -> DeadlineCondition:
    """Classifica a próxima retirada, preservando a tolerância positiva de 30 horas."""

    if now > maximum_end_at:
        return DeadlineCondition.OVERDUE
    if now >= nominal_end_at:
        return DeadlineCondition.IN_TOLERANCE
    if now.date() == nominal_end_at.date():
        return DeadlineCondition.DUE_TODAY
    return DeadlineCondition.ON_TIME
