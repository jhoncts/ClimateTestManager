"""Testes do caso de uso de cadastro de ensaio."""

import unittest
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import select

from climatetest_manager.database.models import ClimateTestRecord
from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.climate_tests import ClimateTestRepository
from climatetest_manager.services.climate_tests import (
    ClimateTestService,
    ClimateTestValidationError,
    CreateClimateTestCommand,
)


def _command(**changes: str) -> CreateClimateTestCommand:
    values = {
        "client": "Cliente Exemplo",
        "process_number": "26000.001/2026-10",
        "product": "Luminária",
        "ex_marking": "Ex db IIC T6 Gb",
        "epl": "Gb",
        "tamb_max_c": "40",
        "delta_t_max_k": "35",
        "selected_option": "B",
        "notes": "Cadastro de teste",
    }
    values.update(changes)
    return CreateClimateTestCommand(**values)


class ClimateTestServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "service.db"
        self.engine = initialize_database(database_path)
        self.session_factory = create_session_factory(self.engine)
        repository = ClimateTestRepository(self.session_factory)
        self.service = ClimateTestService(repository)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temporary_directory.cleanup()

    def test_creates_test_with_rule_snapshot_and_audit(self) -> None:
        test_id = self.service.create(_command(), actor="João")

        with self.session_factory() as session:
            stored = session.scalar(select(ClimateTestRecord))

            self.assertIsNotNone(stored)
            self.assertEqual(stored.id, test_id)
            self.assertEqual(stored.service_temperature_c, Decimal("75.00"))
            self.assertEqual(stored.condition_snapshot.rule_id, "G1-HIGH-B")
            self.assertEqual(stored.condition_snapshot.chamber_duration_hours, 504)
            self.assertEqual(stored.condition_snapshot.drying_temperature_c, Decimal("95.00"))
            self.assertEqual(stored.audit_events[0].actor, "João")

    def test_accepts_comma_as_decimal_separator(self) -> None:
        self.service.create(_command(tamb_max_c="40,5", delta_t_max_k="29,5", selected_option="A"))

        recent = self.service.list_recent()
        self.assertEqual(recent[0].service_temperature_c, "70.00")
        self.assertEqual(recent[0].selected_option, "A")

    def test_blank_tamb_is_stored_as_positive_40_with_audit_reason(self) -> None:
        self.service.create(_command(tamb_max_c=""), actor="João")

        with self.session_factory() as session:
            stored = session.scalar(select(ClimateTestRecord))

            self.assertEqual(stored.tamb_max_c, Decimal("40.00"))
            self.assertEqual(stored.service_temperature_c, Decimal("75.00"))
            self.assertIn("adotada conforme Tabela 1", stored.audit_events[0].new_value)

    def test_rejects_missing_required_field(self) -> None:
        with self.assertRaisesRegex(ClimateTestValidationError, "Cliente"):
            self.service.create(_command(client="  "))

    def test_dashboard_starts_without_active_tests(self) -> None:
        self.service.create(_command())

        summary = self.service.dashboard_summary()

        self.assertEqual(summary.in_progress, 0)
        self.assertEqual(summary.drying, 0)


if __name__ == "__main__":
    unittest.main()
