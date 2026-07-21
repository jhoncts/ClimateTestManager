"""Entidades e regras de negócio independentes de interface e persistência."""

from climatetest_manager.domain.climate_rules import (
    NORMATIVE_RULE_VERSION,
    ClimateCondition,
    ClimateRuleError,
    PhaseCondition,
    available_options,
    calculate_condition,
    calculate_service_temperature,
    resolve_condition,
)
from climatetest_manager.domain.enums import (
    EPL,
    DeadlineCondition,
    TestOption,
    TestSituation,
)

__all__ = [
    "NORMATIVE_RULE_VERSION",
    "ClimateCondition",
    "ClimateRuleError",
    "DeadlineCondition",
    "EPL",
    "PhaseCondition",
    "TestOption",
    "TestSituation",
    "available_options",
    "calculate_condition",
    "calculate_service_temperature",
    "resolve_condition",
]
