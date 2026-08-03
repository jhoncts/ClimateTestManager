"""Testes das convenções de apresentação da interface."""

import unittest
from datetime import datetime
from decimal import Decimal

from climatetest_manager.domain.enums import ConditionInputMode
from climatetest_manager.ui.formatters import (
    format_condition_source,
    format_decimal,
    format_duration_detail,
    format_hours_as_days,
    format_operational_date,
    format_thermal_summary,
    format_weekday,
    normalize_date_input,
    normalize_decimal_input,
    normalize_time_input,
)


class FormatterTests(unittest.TestCase):
    def test_formats_decimal_with_brazilian_separator_without_losing_integer_zeros(self) -> None:
        self.assertEqual(format_decimal(Decimal("90.00")), "90")
        self.assertEqual(format_decimal(Decimal("140")), "140")
        self.assertEqual(format_decimal(Decimal("40.50")), "40,5")

    def test_normalizes_typed_decimal_values(self) -> None:
        self.assertEqual(normalize_decimal_input("35.5 abc"), "35,5")
        self.assertEqual(
            normalize_decimal_input("-20.5 °C", allow_negative=True),
            "-20,5",
        )
        self.assertEqual(normalize_decimal_input("1,2,3"), "1,23")

    def test_applies_and_limits_brazilian_date_mask(self) -> None:
        self.assertEqual(normalize_date_input("06072026"), "06/07/2026")
        self.assertEqual(normalize_date_input("06/07/2026"), "06/07/2026")
        self.assertEqual(normalize_date_input("060"), "06/0")
        self.assertEqual(normalize_date_input("060720261234"), "06/07/2026")
        self.assertEqual(normalize_date_input(""), "")

    def test_applies_and_limits_time_mask(self) -> None:
        self.assertEqual(normalize_time_input("1430"), "14:30")
        self.assertEqual(normalize_time_input("14:30"), "14:30")
        self.assertEqual(normalize_time_input("143099"), "14:30")
        self.assertEqual(normalize_time_input(""), "")

    def test_formats_hours_as_days(self) -> None:
        self.assertEqual(format_hours_as_days(24), "1 dia")
        self.assertEqual(format_hours_as_days(504), "21 dias")
        self.assertEqual(format_hours_as_days(534), "22 dias e 6 horas")

    def test_formats_nominal_duration_and_upper_limit(self) -> None:
        self.assertEqual(
            format_duration_detail(504, 30),
            "21 dias nominais • limite: 22 dias e 6 horas",
        )

    def test_formats_weekday_without_using_windows_locale(self) -> None:
        monday = datetime(2026, 8, 3, 9, 24)
        sunday = datetime(2026, 8, 9, 15, 30)

        self.assertEqual(format_weekday(monday), "segunda-feira")
        self.assertEqual(format_weekday(sunday), "domingo")
        self.assertEqual(
            format_operational_date(monday),
            ("segunda-feira", "03/08/2026", "09:24"),
        )

    def test_rejects_negative_duration(self) -> None:
        with self.assertRaisesRegex(ValueError, "negativa"):
            format_hours_as_days(-1)

    def test_simplified_modes_do_not_display_fictitious_zero_ts(self) -> None:
        summary = format_thermal_summary(
            input_mode=ConditionInputMode.DIRECT_CONFIGURATION.value,
            epl="",
            service_temperature_c=Decimal("0"),
            ts_reference=None,
            selected_option="-",
        )

        self.assertEqual(summary, "Condição personalizada")
        self.assertNotIn("Ts 0", summary)
        self.assertEqual(
            format_condition_source(ConditionInputMode.PLAN_CRITERION.value),
            "Personalizado",
        )


if __name__ == "__main__":
    unittest.main()
