"""Regras puras do fluxo opcional de acondicionamento e resistência térmica ao frio."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

DEFAULT_MIN_AMBIENT_SERVICE_TEMPERATURE_C = Decimal("-20")
COLD_REDUCTION_MIN_K = Decimal("5")
COLD_REDUCTION_MAX_K = Decimal("10")
CONDITIONING_MIN_HOURS = 24
CONDITIONING_MAX_HOURS = 72
COLD_NOMINAL_HOURS = 24
COLD_MAX_HOURS = 26


class ColdFlowValidationError(ValueError):
    """Indica entrada inválida para o fluxo térmico ao frio."""


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """Janela nominal/máxima calculada a partir do instante real de início."""

    started_at: datetime
    nominal_end_at: datetime
    maximum_end_at: datetime


@dataclass(frozen=True, slots=True)
class ColdTemperatureRange:
    """Faixa permitida para a temperatura inferior de ensaio."""

    minimum_c: Decimal
    maximum_c: Decimal


def parse_minimum_ambient_service_temperature(value: str) -> Decimal:
    """Aceita vírgula decimal e aplica -20 °C quando o campo estiver vazio."""

    normalized = value.strip().replace(",", ".")
    if not normalized:
        return DEFAULT_MIN_AMBIENT_SERVICE_TEMPERATURE_C
    try:
        temperature = Decimal(normalized)
    except InvalidOperation as error:
        raise ColdFlowValidationError(
            "Temperatura mínima ambiente de serviço deve ser um número válido."
        ) from error
    if not temperature.is_finite():
        raise ColdFlowValidationError(
            "Temperatura mínima ambiente de serviço deve ser um número finito."
        )
    return temperature


def cold_temperature_range(minimum_ambient_service_temperature_c: Decimal) -> ColdTemperatureRange:
    """Calcula Tmin ambiente -5 K a -10 K, ordenando do valor mais frio ao mais quente."""

    minimum_c = minimum_ambient_service_temperature_c - COLD_REDUCTION_MAX_K
    maximum_c = minimum_ambient_service_temperature_c - COLD_REDUCTION_MIN_K
    return ColdTemperatureRange(minimum_c=minimum_c, maximum_c=maximum_c)


def conditioning_window(started_at: datetime) -> TimeWindow:
    """Retorna a janela de 24 h a 72 h do acondicionamento pós-calor."""

    normalized = started_at.replace(microsecond=0)
    return TimeWindow(
        started_at=normalized,
        nominal_end_at=normalized + timedelta(hours=CONDITIONING_MIN_HOURS),
        maximum_end_at=normalized + timedelta(hours=CONDITIONING_MAX_HOURS),
    )


def cold_window(started_at: datetime) -> TimeWindow:
    """Retorna a retirada nominal em 24 h e o limite em 26 h do ensaio de frio."""

    normalized = started_at.replace(microsecond=0)
    return TimeWindow(
        started_at=normalized,
        nominal_end_at=normalized + timedelta(hours=COLD_NOMINAL_HOURS),
        maximum_end_at=normalized + timedelta(hours=COLD_MAX_HOURS),
    )
