"""Testes das saídas CSV/ICS e da entrega idempotente de avisos."""

import json
import smtplib
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from climatetest_manager.config import EmailSettings
from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.climate_tests import ClimateTestRepository
from climatetest_manager.services.climate_tests import (
    ClimateTestService,
    CreateClimateTestCommand,
)
from climatetest_manager.services.exports import (
    build_database_backup_bytes,
    create_configured_database_backups,
    create_daily_database_backup,
    export_test_calendar,
    export_tests_csv,
    verify_sqlite_database,
)
from climatetest_manager.services.notifications import (
    SMTP_LOCAL_HOSTNAME,
    EmailNotificationProvider,
    deliver_due_notifications,
)


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


class FailingProvider:
    def send(self, title: str, message: str) -> None:
        raise RuntimeError("servidor indisponível")


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

    def test_warns_two_hours_before_nominal_removal_with_process_summary(self) -> None:
        test_id = self.service.create(_command())
        self.service.start_chamber(test_id)
        provider = RecordingProvider()
        self.now += timedelta(hours=502)

        result = deliver_due_notifications(
            self.repository,
            provider,
            now_provider=lambda: self.now,
        )

        self.assertEqual(result, (1, 0))
        title, message = provider.messages[0]
        self.assertIn("em 2 horas", title)
        self.assertIn("Cliente: Cliente Demonstração", message)
        self.assertIn("Produto: Luminária", message)
        self.assertIn("Processo: 26123.1", message)
        self.assertIn("Amostras: 1", message)

    def test_completed_channel_is_not_repeated_when_email_recovers(self) -> None:
        test_id = self.service.create(_command())
        self.service.start_chamber(test_id)
        self.now += timedelta(hours=502)
        desktop = RecordingProvider()

        first = deliver_due_notifications(
            self.repository,
            desktop,
            email_provider=FailingProvider(),
            now_provider=lambda: self.now,
        )
        email = RecordingProvider()
        second = deliver_due_notifications(
            self.repository,
            desktop,
            email_provider=email,
            now_provider=lambda: self.now,
        )

        self.assertEqual(first, (0, 1))
        self.assertEqual(second, (1, 0))
        self.assertEqual(len(desktop.messages), 1)
        self.assertEqual(len(email.messages), 1)

    def test_server_email_and_interactive_desktop_workers_complete_same_event(self) -> None:
        test_id = self.service.create(_command())
        self.service.start_chamber(test_id)
        self.now += timedelta(hours=502)
        email = RecordingProvider()
        desktop = RecordingProvider()

        email_result = deliver_due_notifications(
            self.repository,
            None,
            email_provider=email,
            require_desktop=True,
            require_email=True,
            now_provider=lambda: self.now,
        )
        desktop_result = deliver_due_notifications(
            self.repository,
            desktop,
            require_desktop=True,
            require_email=True,
            now_provider=lambda: self.now,
        )
        repeated_email_result = deliver_due_notifications(
            self.repository,
            None,
            email_provider=email,
            require_desktop=True,
            require_email=True,
            now_provider=lambda: self.now,
        )

        self.assertEqual(email_result, (0, 0))
        self.assertEqual(desktop_result, (1, 0))
        self.assertEqual(repeated_email_result, (0, 0))
        self.assertEqual(len(email.messages), 1)
        self.assertEqual(len(desktop.messages), 1)

    def test_email_provider_sends_to_all_active_recipients_with_tls(self) -> None:
        settings = EmailSettings(
            enabled=True,
            host="smtp.example.com",
            port=587,
            sender="laboratorio@example.com",
            username="usuario-smtp",
            password="segredo",
            use_tls=True,
        )
        provider = EmailNotificationProvider(
            settings,
            ["admin@example.com", "operador@example.com", "admin@example.com"],
        )

        with patch("climatetest_manager.services.notifications.smtplib.SMTP") as smtp:
            client = smtp.return_value.__enter__.return_value
            client.send_message.return_value = {}
            receipt = provider.send("Retirada em 2 horas", "Processo: 26123.1")

        smtp.assert_called_once_with(
            "smtp.example.com",
            587,
            local_hostname=SMTP_LOCAL_HOSTNAME,
            timeout=20,
        )
        client.starttls.assert_called_once_with()
        client.login.assert_called_once_with("usuario-smtp", "segredo")
        message = client.send_message.call_args.args[0]
        self.assertEqual(message["To"], "admin@example.com, operador@example.com")
        self.assertTrue(message["Date"])
        self.assertTrue(message["Message-ID"])
        plain_body = message.get_body(preferencelist=("plain",))
        html_body = message.get_body(preferencelist=("html",))
        self.assertIsNotNone(plain_body)
        self.assertIsNotNone(html_body)
        self.assertIn("Processo: 26123.1", plain_body.get_content())
        self.assertIn("ClimateTest Manager", html_body.get_content())
        self.assertIn("26123.1", html_body.get_content())
        self.assertEqual(
            client.send_message.call_args.kwargs,
            {
                "from_addr": "laboratorio@example.com",
                "to_addrs": ["admin@example.com", "operador@example.com"],
            },
        )
        self.assertEqual(receipt.recipients, ("admin@example.com", "operador@example.com"))
        self.assertEqual(receipt.message_id, message["Message-ID"])

    def test_email_provider_ignores_accented_windows_computer_name(self) -> None:
        """O EHLO não pode depender de um nome local que talvez contenha acento."""

        settings = EmailSettings(
            enabled=True,
            host="smtp.gmail.com",
            port=587,
            sender="climatetest.sender@gmail.com",
            username="climatetest.sender@gmail.com",
            password="abcdefghijklmnop",
            use_tls=True,
        )
        provider = EmailNotificationProvider(settings, ["admin@example.com"])
        local_hostnames: list[str | None] = []

        class AccentSensitiveSMTP:
            def __init__(
                self,
                _host: str,
                _port: int,
                *,
                local_hostname: str | None = None,
                timeout: int,
            ) -> None:
                del timeout
                local_hostnames.append(local_hostname)
                (local_hostname or "computador-com-ó").encode("ascii")

            def __enter__(self) -> "AccentSensitiveSMTP":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def ehlo(self) -> None:
                return None

            def starttls(self) -> None:
                return None

            def login(self, _username: str, _password: str) -> None:
                return None

            def send_message(
                self,
                _message: object,
                *,
                from_addr: str,
                to_addrs: list[str],
            ) -> dict[str, object]:
                del from_addr, to_addrs
                return {}

        with patch(
            "climatetest_manager.services.notifications.smtplib.SMTP",
            AccentSensitiveSMTP,
        ):
            provider.send("Teste", "Mensagem")

        self.assertEqual(local_hostnames, [SMTP_LOCAL_HOSTNAME])
        SMTP_LOCAL_HOSTNAME.encode("ascii")

    def test_gmail_provider_removes_spaces_from_app_password(self) -> None:
        settings = EmailSettings(
            enabled=True,
            host="smtp.gmail.com",
            port=587,
            sender="climatetest.sender@gmail.com",
            username="climatetest.sender@gmail.com",
            password="abcd efgh ijkl mnop",
            use_tls=True,
        )
        provider = EmailNotificationProvider(settings, ["admin@example.com"])

        with patch("climatetest_manager.services.notifications.smtplib.SMTP") as smtp:
            client = smtp.return_value.__enter__.return_value
            client.send_message.return_value = {}
            provider.send("Teste", "Mensagem")

        client.login.assert_called_once_with(
            "climatetest.sender@gmail.com",
            "abcdefghijklmnop",
        )

    def test_email_provider_reports_refused_recipient(self) -> None:
        settings = EmailSettings(
            enabled=True,
            host="smtp.example.com",
            port=587,
            sender="laboratorio@example.com",
            username="usuario-smtp",
            password="segredo",
            use_tls=True,
        )
        provider = EmailNotificationProvider(
            settings,
            ["aceito@example.com", "recusado@example.com"],
        )

        with (
            patch("climatetest_manager.services.notifications.smtplib.SMTP") as smtp,
            self.assertRaisesRegex(RuntimeError, "recusado@example.com"),
        ):
            client = smtp.return_value.__enter__.return_value
            client.send_message.return_value = {
                "recusado@example.com": (550, b"Mailbox unavailable")
            }
            provider.send("Teste", "Mensagem")

    def test_email_provider_explains_non_ascii_credentials(self) -> None:
        settings = EmailSettings(
            enabled=True,
            host="smtp.gmail.com",
            port=587,
            sender="climatetest.sender@gmail.com",
            username="climatetest.sender@gmail.com",
            password="senha-com-ó",
            use_tls=True,
        )
        provider = EmailNotificationProvider(settings, ["admin@example.com"])

        with self.assertRaisesRegex(ValueError, "contém acento"):
            provider.send("Teste", "Mensagem")

    def test_gmail_authentication_rejection_has_actionable_message(self) -> None:
        settings = EmailSettings(
            enabled=True,
            host="smtp.gmail.com",
            port=587,
            sender="climatetest.sender@gmail.com",
            username="climatetest.sender@gmail.com",
            password="abcdefghijklmnop",
            use_tls=True,
        )
        provider = EmailNotificationProvider(settings, ["admin@example.com"])

        with (
            patch("climatetest_manager.services.notifications.smtplib.SMTP") as smtp,
            self.assertRaisesRegex(RuntimeError, "Gmail recusou a autenticação"),
        ):
            client = smtp.return_value.__enter__.return_value
            client.login.side_effect = smtplib.SMTPAuthenticationError(
                535,
                b"5.7.8 Username and Password not accepted",
            )
            provider.send("Teste", "Mensagem")

    def test_creates_consistent_database_backup(self) -> None:
        self.service.create(_command())

        backup = build_database_backup_bytes(self.directory / "test.db")

        self.assertTrue(backup.startswith(b"SQLite format 3"))

    def test_creates_only_one_automatic_backup_per_day(self) -> None:
        self.service.create(_command())
        backup_directory = self.directory / "backups"

        first = create_daily_database_backup(
            self.directory / "test.db",
            backup_directory=backup_directory,
            now=self.now,
        )
        second = create_daily_database_backup(
            self.directory / "test.db",
            backup_directory=backup_directory,
            now=self.now + timedelta(hours=2),
        )

        self.assertEqual(first, second)
        self.assertTrue(first.exists())
        self.assertEqual(len(list(backup_directory.glob("*.db"))), 1)
        manifest_path = first.with_suffix(".db.manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["quick_check"], "ok")
        self.assertEqual(manifest["foreign_key_violations"], 0)
        self.assertEqual(len(manifest["sha256"]), 64)

    def test_rebuilds_a_corrupted_daily_backup_and_verifies_it(self) -> None:
        self.service.create(_command())
        backup_directory = self.directory / "backups"
        backup = create_daily_database_backup(
            self.directory / "test.db",
            backup_directory=backup_directory,
            now=self.now,
        )
        backup.write_bytes(b"arquivo corrompido")

        repaired = create_daily_database_backup(
            self.directory / "test.db",
            backup_directory=backup_directory,
            now=self.now + timedelta(hours=1),
        )

        verification = verify_sqlite_database(repaired, verified_at=self.now)
        self.assertEqual(verification.quick_check, "ok")
        self.assertTrue(repaired.read_bytes().startswith(b"SQLite format 3"))

    def test_creates_local_and_external_daily_backups(self) -> None:
        self.service.create(_command())
        external_directory = self.directory / "OneDrive" / "Backups"

        with patch(
            "climatetest_manager.services.exports.get_external_backup_directory",
            return_value=external_directory,
        ):
            backups = create_configured_database_backups(
                self.directory / "test.db",
                now=self.now,
            )

        self.assertEqual(len(backups), 2)
        self.assertEqual(backups[0].parent, self.directory / "backups")
        self.assertEqual(backups[1].parent, external_directory)
        self.assertTrue(all(path.exists() for path in backups))


if __name__ == "__main__":
    unittest.main()
