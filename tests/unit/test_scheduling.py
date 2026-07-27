"""Testes dos horários calculados para uma etapa."""

import unittest
from datetime import datetime
from decimal import Decimal

from climatetest_manager.domain.climate_rules import PhaseCondition
from climatetest_manager.domain.enums import DeadlineCondition
from climatetest_manager.services.scheduling import classify_deadline, schedule_phase


class SchedulePhaseTests(unittest.TestCase):
    def test_calculates_nominal_and_maximum_end(self) -> None:
        start = datetime(2026, 7, 21, 8, 0)
        condition = PhaseCondition(temperature_c=Decimal("80"), duration_hours=672)

        schedule = schedule_phase(start, condition)

        self.assertEqual(schedule.nominal_end_at, datetime(2026, 8, 18, 8, 0))
        self.assertEqual(schedule.maximum_end_at, datetime(2026, 8, 19, 14, 0))

    def test_classifies_nominal_window_as_tolerance_and_only_delays_after_maximum(self) -> None:
        nominal = datetime(2026, 8, 18, 8, 0)
        maximum = datetime(2026, 8, 19, 14, 0)

        self.assertEqual(
            classify_deadline(datetime(2026, 8, 18, 7, 0), nominal, maximum),
            DeadlineCondition.DUE_TODAY,
        )
        self.assertEqual(
            classify_deadline(nominal, nominal, maximum),
            DeadlineCondition.IN_TOLERANCE,
        )
        self.assertEqual(
            classify_deadline(maximum, nominal, maximum),
            DeadlineCondition.IN_TOLERANCE,
        )
        self.assertEqual(
            classify_deadline(datetime(2026, 8, 19, 14, 1), nominal, maximum),
            DeadlineCondition.OVERDUE,
        )


if __name__ == "__main__":
    unittest.main()
