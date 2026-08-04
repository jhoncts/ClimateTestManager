"""Testes leves das telas de acesso e tutorial."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import flet as ft

from climatetest_manager.ui.views.auth import InitialSetupView, LoginView, StorageSetupView
from climatetest_manager.ui.views.onboarding import STEPS, OnboardingView


class AuthenticationViewTests(unittest.TestCase):
    def test_login_forwards_credentials_and_remember_choice(self) -> None:
        received: list[tuple[str, str, bool]] = []
        view = LoginView(
            lambda login, password, remember: received.append((login, password, remember))
        )
        view.login.value = "operador"
        view.password.value = "Senha123"
        view.remember.value = True
        view._submit()

        self.assertIsInstance(view.root, ft.Container)
        self.assertEqual(received, [("operador", "Senha123", True)])

    def test_first_access_builds_admin_registration(self) -> None:
        commands = []
        view = InitialSetupView(commands.append)
        view.first_name.value = "Jhon"
        view.last_name.value = "Cleiton"
        view.username.value = "jhon"
        view.email.value = "jhon@example.com"
        view.password.value = "Senha123"
        view.confirmation.value = "Senha123"
        view._submit()

        self.assertEqual(commands[0].role, "admin")
        self.assertIsInstance(view.root.content.content, ft.ResponsiveRow)

    def test_access_sidebar_uses_readable_contained_security_cards(self) -> None:
        view = LoginView(lambda _login, _password, _remember: None)
        shell = view.root.content.content
        brand_panel = shell.controls[0]
        brand = brand_panel.content
        security_cards = [
            control
            for control in brand.controls
            if isinstance(control, ft.Container) and isinstance(control.content, ft.Row)
        ]

        self.assertEqual(len(security_cards), 3)
        for card in security_cards:
            message = card.content.controls[1]
            self.assertEqual(message.color, "#ECFEFF")
            self.assertTrue(message.expand)
            self.assertIsNotNone(card.padding)
            self.assertIsNotNone(card.margin)

    def test_storage_setup_requires_informed_confirmation(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            received: list[tuple[Path, Path | None]] = []
            view = StorageSetupView(
                default_data_directory=root / "dados",
                suggested_backup_directory=root / "OneDrive" / "Backups",
                on_confirm=lambda data, backup: received.append((data, backup)),
            )

            view._submit()
            self.assertEqual(received, [])
            self.assertIn("Confirme", view.error.value)

            view.acknowledgement.value = True
            view._submit()

            self.assertEqual(
                received,
                [(root / "dados", root / "OneDrive" / "Backups")],
            )

    def test_help_is_task_oriented_and_first_access_completes(self) -> None:
        completed: list[bool] = []
        view = OnboardingView(
            user_name="Jhon",
            on_complete=lambda: completed.append(True),
            first_access=True,
        )
        view._on_complete()

        self.assertGreaterEqual(len(STEPS), 6)
        self.assertIn("cadastrar um novo ensaio", STEPS[0].title.lower())
        self.assertIsInstance(view.root, ft.Column)
        self.assertEqual(completed, [True])


if __name__ == "__main__":
    unittest.main()
