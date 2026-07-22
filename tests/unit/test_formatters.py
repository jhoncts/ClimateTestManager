"""Testes das convenções de apresentação da interface."""

import unittest
from decimal import Decimal

from climatetest_manager.ui.formatters import (
    format_decimal,
    format_duration_detail,
    format_hours_as_days,
    normalize_decimal_input,
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

    def test_formats_hours_as_days(self) -> None:
        self.assertEqual(format_hours_as_days(24), "1 dia")
        self.assertEqual(format_hours_as_days(504), "21 dias")
        self.assertEqual(format_hours_as_days(534), "22 dias e 6 horas")

    def test_formats_nominal_duration_and_upper_limit(self) -> None:
        self.assertEqual(
            format_duration_detail(504, 30),
            "21 dias nominais • limite: 22 dias e 6 horas",
        )

    def test_rejects_negative_duration(self) -> None:
        with self.assertRaisesRegex(ValueError, "negativa"):
            format_hours_as_days(-1)


if __name__ == "__main__":
    unittest.main()
