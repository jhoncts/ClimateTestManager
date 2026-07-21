"""Cálculo de horários nominais e máximos das etapas."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from climatetest_manager.domain.climate_rules import PhaseCondition


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
