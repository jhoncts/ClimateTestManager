from datetime import datetime
from decimal import Decimal

import pytest

from climatetest_manager.domain.cold_flow import (
    ColdFlowValidationError,
    cold_temperature_range,
    cold_window,
    conditioning_window,
    parse_minimum_ambient_service_temperature,
)


def test_minimum_ambient_service_temperature_defaults_to_minus_20() -> None:
    assert parse_minimum_ambient_service_temperature("") == Decimal("-20")


def test_minimum_ambient_service_temperature_accepts_decimal_comma() -> None:
    assert parse_minimum_ambient_service_temperature("-22,5") == Decimal("-22.5")


def test_minimum_ambient_service_temperature_rejects_invalid_value() -> None:
    with pytest.raises(ColdFlowValidationError):
        parse_minimum_ambient_service_temperature("abc")


def test_cold_temperature_range_for_minus_20_is_minus_30_to_minus_25() -> None:
    result = cold_temperature_range(Decimal("-20"))

    assert result.minimum_c == Decimal("-30")
    assert result.maximum_c == Decimal("-25")


def test_conditioning_window_is_24_to_72_hours() -> None:
    started_at = datetime(2026, 8, 19, 8, 30, 15, 123456)

    result = conditioning_window(started_at)

    assert result.started_at == datetime(2026, 8, 19, 8, 30, 15)
    assert result.nominal_end_at == datetime(2026, 8, 20, 8, 30, 15)
    assert result.maximum_end_at == datetime(2026, 8, 22, 8, 30, 15)


def test_cold_window_is_24_to_26_hours() -> None:
    started_at = datetime(2026, 8, 19, 10, 0)

    result = cold_window(started_at)

    assert result.nominal_end_at == datetime(2026, 8, 20, 10, 0)
    assert result.maximum_end_at == datetime(2026, 8, 20, 12, 0)
