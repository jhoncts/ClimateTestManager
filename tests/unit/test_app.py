"""Teste de montagem da janela principal sem abrir uma janela real."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import flet as ft

from climatetest_manager.app import ClimateTestApplication, _application_theme, main
from climatetest_manager.config import EmailSettings
from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.climate_tests import ClimateTestRepository
from climatetest_manager.repositories.users import UserRepository
from climatetest_manager.services.auth import (
    AuthenticationService,
    UserRegistrationCommand,
)
from climatetest_manager.services.climate_tests import CreateClimateTestCommand
from climatetest_manager.services.notifications import EmailDeliveryReceipt


class FakePage:
    """Implementação mínima das operações usadas pelo controlador da aplicação."""

    def __init__(self) -> None:
        self.window = SimpleNamespace()
        self.controls: list[ft.Control] = []
        self.update_count = 0
        self.scheduled_tasks: list[tuple[object, tuple[object, ...], dict[str, object]]] = []
        self.dialogs: list[ft.AlertDialog] = []
        self.on_close = None

    def add(self, *controls: ft.Control) -> None:
        self.controls.extend(controls)

    def clean(self) -> None:
        self.controls.clear()

    def update(self) -> None:
        self.update_count += 1

    def show_dialog(self, dialog: ft.AlertDialog) -> None:
        self.dialogs.append(dialog)

    def pop_dialog(self) -> None:
        if self.dialogs:
            self.dialogs.pop()

    def run_task(
        self,
        handler: object,
        *args: object,
        **kwargs: object,
    ) -> None:
        self.scheduled_tasks.append((handler, args, kwargs))


class ApplicationTests(unittest.TestCase):
    def test_main_builds_first_access_and_database(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            page = FakePage()
            with patch.dict("os.environ", {"CLIMATETEST_DATA_DIR": temporary_directory}):
                main(page)  # type: ignore[arg-type]

            self.assertEqual(len(page.controls), 1)
            self.assertIsInstance(page.controls[0], ft.AnimatedSwitcher)
            self.assertIsInstance(page.controls[0].content, ft.Container)
            self.assertGreaterEqual(page.update_count, 1)
            self.assertTrue(Path(temporary_directory, "climatetest_manager.db").exists())
            self.assertEqual(
                len(list(Path(temporary_directory, "backups").glob("climatetest_auto_*.db"))),
                1,
            )
            self.assertIsNotNone(page.on_close)
            self.assertEqual(_application_theme().font_family, "Segoe UI")
            page.on_close(None)

    def test_main_requests_storage_choice_before_creating_database(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            page = FakePage()
            default_directory = Path(temporary_directory) / "dados"
            with (
                patch("climatetest_manager.app.storage_setup_required", return_value=True),
                patch(
                    "climatetest_manager.app.get_default_data_directory",
                    return_value=default_directory,
                ),
                patch(
                    "climatetest_manager.app.suggest_onedrive_backup_directory",
                    return_value=Path(temporary_directory) / "OneDrive" / "Backups",
                ),
            ):
                main(page)  # type: ignore[arg-type]

            self.assertEqual(len(page.controls), 1)
            self.assertIsInstance(page.controls[0], ft.Container)
            self.assertFalse((default_directory / "climatetest_manager.db").exists())

    def test_authenticated_application_builds_main_views(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            engine = initialize_database(Path(temporary_directory) / "application.db")
            session_factory = create_session_factory(engine)
            auth = AuthenticationService(UserRepository(session_factory))
            user = auth.register_initial_admin(
                UserRegistrationCommand(
                    username="admin",
                    email="admin@example.com",
                    first_name="Admin",
                    last_name="Local",
                    password="Senha123",
                    password_confirmation="Senha123",
                )
            )
            user = auth.complete_onboarding(user)
            page = FakePage()
            application = ClimateTestApplication(
                page,  # type: ignore[arg-type]
                ClimateTestRepository(session_factory),
                auth_service=auth,
                current_user=user,
                session_token=None,
                theme_mode="light",
                on_signed_out=lambda: None,
            )

            try:
                application.start()
                self.assertIsInstance(page.controls[0], ft.AnimatedSwitcher)
                self.assertEqual(page.controls[0].duration, 0)
                self.assertEqual(page.controls[0].reverse_duration, 0)
                self.assertIsInstance(page.controls[0].content, ft.Container)
                dashboard_content = application._current_content
                application._handle_resize(SimpleNamespace(width=900))
                compact_shell = application._screen_container.content
                self.assertEqual(application._layout.mode, "compact")
                self.assertIs(compact_shell.controls[1].content, dashboard_content)
                application._handle_resize(SimpleNamespace(width=1600))
                self.assertEqual(application._layout.mode, "spacious")
                application._toggle_sidebar()
                self.assertTrue(application._sidebar_collapsed)
                self.assertEqual(application._screen_container.content.controls[0].width, 84)
                self.assertIs(
                    application._screen_container.content.controls[1].content,
                    dashboard_content,
                )
                application._toggle_sidebar()
                self.assertFalse(application._sidebar_collapsed)
                application.show_settings()
                self.assertIsInstance(page.controls[0], ft.AnimatedSwitcher)
                application.show_users()
                self.assertIsInstance(page.controls[0], ft.AnimatedSwitcher)
            finally:
                engine.dispose()

    def test_resize_preserves_scroll_and_ignores_small_width_jitter(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            engine = initialize_database(Path(temporary_directory) / "application.db")
            session_factory = create_session_factory(engine)
            auth = AuthenticationService(UserRepository(session_factory))
            user = auth.register_initial_admin(
                UserRegistrationCommand(
                    username="admin",
                    email="admin@example.com",
                    first_name="Admin",
                    last_name="Local",
                    password="Senha123",
                    password_confirmation="Senha123",
                )
            )
            user = auth.complete_onboarding(user)
            page = FakePage()
            page.width = 1280
            application = ClimateTestApplication(
                page,  # type: ignore[arg-type]
                ClimateTestRepository(session_factory),
                auth_service=auth,
                current_user=user,
                session_token=None,
                theme_mode="light",
                on_signed_out=lambda: None,
            )

            try:
                application.start()
                application._remember_scroll_position(SimpleNamespace(pixels=430))
                original_shell = application._screen_container.content
                application._handle_resize(SimpleNamespace(width=1170))
                self.assertIs(application._screen_container.content, original_shell)
                self.assertEqual(page.scheduled_tasks, [])

                application._handle_resize(SimpleNamespace(width=900))
                self.assertEqual(application._layout.mode, "compact")
                self.assertEqual(len(page.scheduled_tasks), 1)
                self.assertEqual(page.scheduled_tasks[0][2]["offset"], 430)
                self.assertEqual(page.scheduled_tasks[0][2]["duration"], 0)
            finally:
                engine.dispose()

    def test_authenticated_application_builds_every_main_screen(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            engine = initialize_database(Path(temporary_directory) / "application.db")
            session_factory = create_session_factory(engine)
            auth = AuthenticationService(UserRepository(session_factory))
            user = auth.register_initial_admin(
                UserRegistrationCommand(
                    username="admin",
                    email="admin@example.com",
                    first_name="Admin",
                    last_name="Local",
                    password="Senha123",
                    password_confirmation="Senha123",
                )
            )
            user = auth.complete_onboarding(user)
            page = FakePage()
            application = ClimateTestApplication(
                page,  # type: ignore[arg-type]
                ClimateTestRepository(session_factory),
                auth_service=auth,
                current_user=user,
                session_token=None,
                theme_mode="light",
                on_signed_out=lambda: None,
            )

            try:
                test_id = application._service.create(
                    CreateClimateTestCommand(
                        client="Cliente Visual",
                        process_number="26123.1",
                        product="Luminária",
                        epl="Gb",
                        tamb_max_c="40",
                        delta_t_max_k="35",
                        selected_option="B",
                    )
                )
                screens = [
                    ("dashboard", application.show_dashboard),
                    ("tests", application.show_tests),
                    ("details", lambda: application.show_details(test_id)),
                    ("agenda", application.show_agenda),
                    ("history", application.show_history),
                    ("settings", application.show_settings),
                    ("users", application.show_users),
                    ("help", application.show_help),
                    ("new_test", application.show_new_test),
                ]
                for expected_view, show_screen in screens:
                    show_screen()
                    self.assertEqual(application._selected_view, expected_view)
                    self.assertIsInstance(application._current_content, ft.Control)
                    self.assertIs(
                        application._screen_container.content.controls[1].content,
                        application._current_content,
                    )
            finally:
                engine.dispose()

    def test_important_navigation_actions_require_confirmation(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            engine = initialize_database(Path(temporary_directory) / "application.db")
            session_factory = create_session_factory(engine)
            auth = AuthenticationService(UserRepository(session_factory))
            user = auth.register_initial_admin(
                UserRegistrationCommand(
                    username="admin",
                    email="admin@example.com",
                    first_name="Admin",
                    last_name="Local",
                    password="Senha123",
                    password_confirmation="Senha123",
                )
            )
            user = auth.complete_onboarding(user)
            signed_out: list[bool] = []
            page = FakePage()
            application = ClimateTestApplication(
                page,  # type: ignore[arg-type]
                ClimateTestRepository(session_factory),
                auth_service=auth,
                current_user=user,
                session_token=None,
                theme_mode="light",
                on_signed_out=lambda: signed_out.append(True),
            )

            try:
                application.start()
                application._confirm_logout()

                self.assertEqual(signed_out, [])
                self.assertEqual(
                    page.dialogs[-1].title.controls[1].controls[0].value,
                    "Sair da conta?",
                )
                page.dialogs[-1].actions[-1].on_click()
                self.assertEqual(signed_out, [True])

                application.show_new_test()
                application._confirm_discard_new_test()
                self.assertEqual(application._selected_view, "new_test")
                self.assertEqual(
                    page.dialogs[-1].title.controls[1].controls[0].value,
                    "Descartar o novo ensaio?",
                )
            finally:
                engine.dispose()

    def test_email_test_includes_sender_and_shows_smtp_receipt(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            engine = initialize_database(Path(temporary_directory) / "application.db")
            session_factory = create_session_factory(engine)
            auth = AuthenticationService(UserRepository(session_factory))
            user = auth.register_initial_admin(
                UserRegistrationCommand(
                    username="admin",
                    email="admin@example.com",
                    first_name="Admin",
                    last_name="Local",
                    password="Senha123",
                    password_confirmation="Senha123",
                )
            )
            page = FakePage()
            application = ClimateTestApplication(
                page,  # type: ignore[arg-type]
                ClimateTestRepository(session_factory),
                auth_service=auth,
                current_user=user,
                session_token=None,
                theme_mode="light",
                on_signed_out=lambda: None,
            )
            settings = EmailSettings(
                enabled=True,
                host="smtp.gmail.com",
                port=587,
                sender="climatetest.sender@gmail.com",
                username="climatetest.sender@gmail.com",
                password="abcdefghijklmnop",
                use_tls=True,
            )
            receipt = EmailDeliveryReceipt(
                recipients=("admin@example.com", "climatetest.sender@gmail.com"),
                message_id="<teste@climatetest.local>",
            )

            try:
                with (
                    patch(
                        "climatetest_manager.app.load_email_settings",
                        return_value=settings,
                    ),
                    patch("climatetest_manager.app.EmailNotificationProvider") as provider,
                ):
                    provider.return_value.send.return_value = receipt
                    application._test_email()

                provider.assert_called_once_with(
                    settings,
                    ["admin@example.com", "climatetest.sender@gmail.com"],
                )
                provider.return_value.send.assert_called_once()
                dialog = page.dialogs[-1]
                self.assertEqual(
                    dialog.title.controls[1].controls[0].value,
                    "Teste aceito pelo servidor",
                )
                content_text = "\n".join(
                    control.value
                    for control in dialog.content.controls
                    if isinstance(control, ft.Text)
                )
                self.assertIn("admin@example.com", content_text)
                self.assertIn("climatetest.sender@gmail.com", content_text)
                self.assertIn("<teste@climatetest.local>", content_text)
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
