"""Alertas de falha da R6 devem alcançar o relator e administradores."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from climatetest_manager.config import EmailSettings
from climatetest_manager.round6_email import _deliver_sync, _incident_recipients


class Round6EmailTests(unittest.TestCase):
    def test_reporter_and_admins_are_deduplicated(self) -> None:
        app = SimpleNamespace(
            _auth_service=SimpleNamespace(
                notification_admin_emails=lambda: ["admin@lab.com", "user@lab.com"]
            ),
            _current_user=SimpleNamespace(email="USER@lab.com"),
        )

        self.assertEqual(
            _incident_recipients(app),
            ["admin@lab.com", "user@lab.com"],
        )

    @patch("climatetest_manager.round6_email.load_email_settings")
    def test_disabled_email_returns_explicit_status(self, load_settings: MagicMock) -> None:
        load_settings.return_value = EmailSettings()
        app = SimpleNamespace()

        status, delivered, failed, recipient_count = _deliver_sync(app)

        self.assertEqual(status, "disabled")
        self.assertEqual((delivered, failed, recipient_count), (0, 0, 0))

    @patch("climatetest_manager.round6_email.deliver_pending_incident_emails")
    @patch("climatetest_manager.round6_email.EmailNotificationProvider")
    @patch("climatetest_manager.round6_email.load_email_settings")
    def test_enabled_email_delivers_to_reporter_and_admins_immediately(
        self,
        load_settings: MagicMock,
        provider: MagicMock,
        deliver: MagicMock,
    ) -> None:
        settings = EmailSettings(
            enabled=True,
            host="smtp.example.com",
            sender="sender@example.com",
            username="sender@example.com",
            password="secret",
        )
        load_settings.return_value = settings
        deliver.return_value = (1, 0)
        repository = object()
        app = SimpleNamespace(
            _repository=repository,
            _auth_service=SimpleNamespace(notification_admin_emails=lambda: ["admin@lab.com"]),
            _current_user=SimpleNamespace(email="reporter@lab.com"),
        )

        status, delivered, failed, recipient_count = _deliver_sync(app)

        provider.assert_called_once_with(
            settings,
            ["admin@lab.com", "reporter@lab.com"],
        )
        deliver.assert_called_once_with(repository, provider.return_value)
        self.assertEqual(status, "attempted")
        self.assertEqual((delivered, failed, recipient_count), (1, 0, 2))


if __name__ == "__main__":
    unittest.main()
