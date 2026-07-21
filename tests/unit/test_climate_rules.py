"""Testes das regras extraídas da Tabela 17."""

import unittest
from decimal import Decimal

from climatetest_manager.domain.climate_rules import (
    ClimateRuleError,
    available_options,
    calculate_condition,
    calculate_service_temperature,
    resolve_condition,
)
from climatetest_manager.domain.enums import EPL
from climatetest_manager.domain.enums import TestOption as ClimateTestOption


class CalculateServiceTemperatureTests(unittest.TestCase):
    def test_calculates_ts_without_float_rounding(self) -> None:
        result = calculate_service_temperature("40", "29.48")

        self.assertEqual(result, Decimal("69.48"))

    def test_rejects_negative_delta_t(self) -> None:
        with self.assertRaisesRegex(ClimateRuleError, "não pode ser negativo"):
            calculate_service_temperature(40, -1)


class GroupOneRulesTests(unittest.TestCase):
    def test_low_band_applies_minimum_of_80_degrees(self) -> None:
        condition = resolve_condition(EPL.GB, 55, ClimateTestOption.A)

        self.assertEqual(condition.chamber.temperature_c, Decimal("80"))
        self.assertEqual(condition.chamber.duration_hours, 672)
        self.assertFalse(condition.requires_drying)

    def test_70_degrees_stays_in_low_band(self) -> None:
        condition = resolve_condition(EPL.GA, 70, ClimateTestOption.A)

        self.assertEqual(condition.rule_id, "G1-LOW-A")
        self.assertEqual(condition.chamber.temperature_c, Decimal("90"))
        self.assertEqual(available_options(EPL.GA, 70), (ClimateTestOption.A,))

    def test_middle_band_allows_both_options(self) -> None:
        self.assertEqual(
            available_options(EPL.DB, "74.99"),
            (ClimateTestOption.A, ClimateTestOption.B),
        )

        option_b = resolve_condition(EPL.DB, "74.99", ClimateTestOption.B)
        self.assertEqual(option_b.chamber.temperature_c, Decimal("90"))
        self.assertEqual(option_b.chamber.duration_hours, 504)
        self.assertEqual(option_b.drying.temperature_c, Decimal("94.99"))

    def test_75_degrees_uses_high_band_as_decided_by_laboratory(self) -> None:
        condition = resolve_condition(EPL.MB, 75, ClimateTestOption.A)

        self.assertEqual(condition.rule_id, "G1-HIGH-A")
        self.assertEqual(condition.chamber.temperature_c, Decimal("95"))
        self.assertEqual(condition.chamber.duration_hours, 336)
        self.assertEqual(condition.drying.temperature_c, Decimal("95"))
        self.assertEqual(condition.drying.duration_hours, 336)

    def test_option_b_is_rejected_when_only_a_is_permitted(self) -> None:
        with self.assertRaisesRegex(ClimateRuleError, "não está disponível"):
            resolve_condition(EPL.GB, 60, ClimateTestOption.B)


class GroupTwoRulesTests(unittest.TestCase):
    def test_gc_low_band_does_not_apply_80_degree_minimum(self) -> None:
        condition = resolve_condition(EPL.GC, 45, ClimateTestOption.A)

        self.assertEqual(condition.chamber.temperature_c, Decimal("55"))
        self.assertEqual(condition.rule_id, "G2-LOW-A")

    def test_80_degrees_stays_in_low_band(self) -> None:
        condition = resolve_condition(EPL.DC, 80, ClimateTestOption.A)

        self.assertEqual(condition.rule_id, "G2-LOW-A")
        self.assertEqual(available_options(EPL.DC, 80), (ClimateTestOption.A,))

    def test_85_degrees_stays_in_middle_band(self) -> None:
        condition = resolve_condition(EPL.GC, 85, ClimateTestOption.B)

        self.assertEqual(condition.rule_id, "G2-MID-B")
        self.assertEqual(condition.chamber.duration_hours, 336)
        self.assertEqual(condition.drying.duration_hours, 336)

    def test_value_above_85_uses_high_band(self) -> None:
        condition = resolve_condition(EPL.GC, "85.01", ClimateTestOption.B)

        self.assertEqual(condition.rule_id, "G2-HIGH-B")
        self.assertEqual(condition.chamber.duration_hours, 504)
        self.assertEqual(condition.drying.temperature_c, Decimal("95.01"))


class ConditionMetadataTests(unittest.TestCase):
    def test_condition_preserves_tolerances_and_normative_version(self) -> None:
        condition = calculate_condition(EPL.GB, 40, 36, ClimateTestOption.A)

        self.assertEqual(condition.service_temperature_c, Decimal("76"))
        self.assertEqual(condition.chamber.maximum_duration_hours, 366)
        self.assertEqual(condition.chamber.humidity_percent, Decimal("90"))
        self.assertEqual(condition.chamber.humidity_tolerance_percent, Decimal("5"))
        self.assertEqual(condition.nominal_total_hours, 672)
        self.assertEqual(condition.normative_rule_version, "IEC60079-0:2020-T17-v1")


if __name__ == "__main__":
    unittest.main()
