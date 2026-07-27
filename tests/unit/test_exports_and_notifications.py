"""Testes das saídas CSV/ICS e da entrega idempotente de avisos."""

import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.climate_tests import ClimateTestRepository
from climatetest_manager.services.climate_tests import (
    ClimateTestService,
    CreateClimateTestCommand,
)
from climatetest_manager.services.exports import (
    build_database_backup_bytes,
    export_test_calendar,
    export_tests_csv,
)
from climatetest_manager.services.notifications import deliver_due_notifications


def _command() -> CreateClimateTestCommand:
    return CreateClimateTestCommand(
        client="Cliente Demonstração",
        process_number="26123.1",
        product="Luminária",
        epl="Gb",
        tamb_max_c="40",
        delta_t_max_k="35",
        selected_option="B",
    )


class RecordingProvider:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send(self, title: str, message: str) -> None:
        self.messages.append((title, message))


class ExportAndNotificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.engine = initialize_database(self.directory / "test.db")
        self.repository = ClimateTestRepository(create_session_factory(self.engine))
        self.now = datetime(2026, 7, 22, 8, 0)
        self.service = ClimateTestService(self.repository, now_provider=lambda: self.now)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temporary_directory.cleanup()

    def test_exports_csv_and_importable_calendar(self) -> None:
        test_id = self.service.create(_command())
        self.service.start_chamber(test_id)

        csv_path = export_tests_csv(
            self.service.list_tests(), output_directory=self.directory / "exports"
        )
        calendar_path = export_test_calendar(
            self.service.get_details(test_id), output_directory=self.directory / "exports"
        )

        csv_content = csv_path.read_text(encoding="utf-8-sig")
        calendar_content = calendar_path.read_text(encoding="utf-8")
        self.assertIn("Cliente Demonstração", csv_content)
        self.assertIn("Retirada recomendada", csv_content)
        self.assertIn("Origem da condição", csv_content)
        self.assertIn("BEGIN:VCALENDAR", calendar_content)
        self.assertIn("Retirar amostra da câmara", calendar_content)
        self.assertIn("TRIGGER:-PT2H", calendar_content)

    def test_delivers_due_notifications_once(self) -> None:
        test_id = self.service.create(_command())
        self.service.start_chamber(test_id)
        self.now += timedelta(hours=600)
        provider = RecordingProvider()

        first_result = deliver_due_notifications(
            self.repository, provider, now_provider=lambda: self.now
        )
        second_result = deliver_due_notifications(
            self.repository, provider, now_provider=lambda: self.now
        )

        self.assertEqual(first_result, (2, 0))
        self.assertEqual(second_result, (0, 0))
        self.assertEqual(len(provider.messages), 2)
        status = self.repository.get_notification_status()
        self.assertEqual(status.last_checked_at, self.now)
        self.assertEqual(status.delivered_count, 0)
        self.assertEqual(status.failed_count, 0)

    def test_creates_consistent_database_backup(self) -> None:
        self.service.create(_command())

        backup = build_database_backup_bytes(self.directory / "test.db")

        self.assertTrue(backup.startswith(b"SQLite format 3"))


if __name__ == "__main__":
    unittest.main()
