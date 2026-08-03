"""Testes de montagem das novas telas operacionais."""

import asyncio
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import PropertyMock, patch

import flet as ft

from climatetest_manager.config import EmailSettings
from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.domain.audit import MAX_REASON_LENGTH
from climatetest_manager.domain.enums import OperationalTimestamp
from climatetest_manager.repositories.climate_tests import (
    ClimateTestRepository,
    NotificationStatus,
    SystemIncidentSummary,
)
from climatetest_manager.services.auth import UserSummary
from climatetest_manager.services.climate_tests import ClimateTestService, CreateClimateTestCommand
from climatetest_manager.ui.components import ReasonSelector, user_avatar
from climatetest_manager.ui.email_help import EMAIL_SETUP_STEPS
from climatetest_manager.ui.views.agenda import AgendaView
from climatetest_manager.ui.views.dashboard import DashboardView
from climatetest_manager.ui.views.history import build_history_view
from climatetest_manager.ui.views.new_test import NewTestView
from climatetest_manager.ui.views.settings import build_settings_view
from climatetest_manager.ui.views.test_details import (
    TestDetailsView as DetailsView,
)
from climatetest_manager.ui.views.test_details import (
    _chamber_start_summary,
    _ts_highlight,
)
from climatetest_manager.ui.views.tests_list import TestsListView as ListView
from climatetest_manager.ui.views.users import UsersView


def _walk_controls(control: ft.Control):
    """Percorre conteúdo simples e coleções usadas nas telas testadas."""

    yield control
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk_controls(content)
    for child in getattr(control, "controls", ()) or ():
        yield from _walk_controls(child)


class OperationalViewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.engine = initialize_database(Path(self.temporary_directory.name) / "views.db")
        repository = ClimateTestRepository(create_session_factory(self.engine))
        self.now = datetime(2026, 7, 22, 8, 0)
        self.service = ClimateTestService(repository, now_provider=lambda: self.now)
        self.test_id = self.service.create(
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

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temporary_directory.cleanup()

    def test_builds_searchable_list_and_filters_results(self) -> None:
        selected: list[int] = []
        exported: list[list[object]] = []

        async def export(items: list[object]) -> None:
            exported.append(items)

        view = ListView(
            self.service.list_tests(),
            on_select=selected.append,
            on_new_test=lambda: None,
            on_export=export,
        )

        self.assertIsInstance(view.root, ft.Column)
        self.assertEqual(len(view.results.controls), 1)
        view.search.value = "inexistente"
        view._refresh()
        self.assertEqual(len(view.results.controls), 1)
        asyncio.run(view._export_matching())
        self.assertEqual(exported, [[]])

    def test_builds_details_and_parses_manual_chamber_time(self) -> None:
        starts: list[datetime | None] = []
        view = DetailsView(
            self.service.get_details(self.test_id),
            on_back=lambda: None,
            on_start_chamber=starts.append,
            on_start_drying=lambda _value: None,
            on_finish=lambda _value: None,
            on_cancel=lambda _reason: None,
            on_edit=lambda: None,
            on_delete=lambda: None,
            on_change_timestamp=lambda _timestamp, _value, _reason: None,
        )
        view.date.value = "22/07/2026"
        view.time.value = "07:45"
        view._manual(starts.append)

        self.assertIsInstance(view.root, ft.Column)
        self.assertEqual(starts, [datetime(2026, 7, 22, 7, 45)])
        self.assertTrue(callable(view._on_cancel))
        summary = view._summary_panel()
        summary_layout = summary.content.controls[-1]
        self.assertIsInstance(summary_layout, ft.ResponsiveRow)

        ts_card = _ts_highlight(self.service.get_details(self.test_id))
        ts_texts = [
            control.value for control in ts_card.content.controls if isinstance(control, ft.Text)
        ]
        self.assertIn("75 °C", ts_texts)
        self.assertTrue(any("Tamb 40 °C" in text for text in ts_texts))

    def test_details_root_avoids_infinite_height_in_summary(self) -> None:
        """Protege a tela real contra STRETCH dentro da coluna rolável."""

        view = DetailsView(
            self.service.get_details(self.test_id),
            on_back=lambda: None,
            on_start_chamber=lambda _value: None,
            on_start_drying=lambda _value: None,
            on_finish=lambda _value: None,
            on_cancel=lambda _reason: None,
            on_edit=lambda: None,
            on_delete=lambda: None,
            on_change_timestamp=lambda _timestamp, _value, _reason: None,
        )

        self.assertEqual(view.root.scroll, ft.ScrollMode.AUTO)
        summary = view.root.controls[1]
        summary_layout = summary.content.controls[-1]
        self.assertIsInstance(summary_layout, ft.ResponsiveRow)
        self.assertEqual(
            summary_layout.vertical_alignment,
            ft.CrossAxisAlignment.START,
            "Uma ResponsiveRow dentro da tela rolável não pode usar STRETCH: "
            "o Flutter tenta aplicar uma altura infinita e deixa a tela em branco.",
        )

    def test_details_masks_and_limits_date_and_time_inputs(self) -> None:
        view = DetailsView(
            self.service.get_details(self.test_id),
            on_back=lambda: None,
            on_start_chamber=lambda _value: None,
            on_start_drying=lambda _value: None,
            on_finish=lambda _value: None,
            on_cancel=lambda _reason: None,
            on_edit=lambda: None,
            on_delete=lambda: None,
            on_change_timestamp=lambda _timestamp, _value, _reason: None,
        )
        view.date.value = "06072026123"
        view.date.on_change()
        view.time.value = "143099"
        view.time.on_change()

        self.assertEqual(view.date.value, "06/07/2026")
        self.assertEqual(view.time.value, "14:30")
        self.assertEqual(view.date.max_length, 10)
        self.assertEqual(view.time.max_length, 5)

    def test_details_emphasizes_client_process_before_test_number(self) -> None:
        view = DetailsView(
            self.service.get_details(self.test_id),
            on_back=lambda: None,
            on_start_chamber=lambda _value: None,
            on_start_drying=lambda _value: None,
            on_finish=lambda _value: None,
            on_cancel=lambda _reason: None,
            on_edit=lambda: None,
            on_delete=lambda: None,
            on_change_timestamp=lambda _timestamp, _value, _reason: None,
        )

        header_texts = [
            control
            for control in _walk_controls(view.root.controls[0])
            if isinstance(control, ft.Text)
        ]
        values = [control.value for control in header_texts]
        identity = header_texts[values.index("Cliente Visual / 26123.1")]
        test_number = header_texts[values.index(f"Ensaio #{self.test_id}")]
        self.assertEqual(identity.weight, ft.FontWeight.BOLD)
        self.assertGreater(identity.size, test_number.size)
        self.assertLess(
            values.index("Cliente Visual / 26123.1"), values.index(f"Ensaio #{self.test_id}")
        )

    def test_details_lists_the_four_operational_records_without_ambiguity(self) -> None:
        self.service.start_chamber(self.test_id, datetime(2026, 5, 27, 10, 0))
        self.service.start_drying(self.test_id, datetime(2026, 7, 1, 12, 0))
        self.service.finish(self.test_id, self.now)
        view = DetailsView(
            self.service.get_details(self.test_id),
            on_back=lambda: None,
            on_start_chamber=lambda _value: None,
            on_start_drying=lambda _value: None,
            on_finish=lambda _value: None,
            on_cancel=lambda _reason: None,
            on_edit=lambda: None,
            on_delete=lambda: None,
            on_change_timestamp=lambda _timestamp, _value, _reason: None,
        )

        self.assertEqual(
            tuple(view._registered_timestamps()),
            (
                OperationalTimestamp.CHAMBER_STARTED,
                OperationalTimestamp.CHAMBER_ENDED,
                OperationalTimestamp.DRYING_STARTED,
                OperationalTimestamp.DRYING_ENDED,
            ),
        )
        self.assertEqual(
            [timestamp.label for timestamp in view._registered_timestamps()],
            [
                "Entrada — Câmara climática",
                "Saída — Câmara climática",
                "Entrada — Câmara seca",
                "Saída — Câmara seca",
            ],
        )

    def test_chamber_confirmation_emphasizes_weekdays_and_weekend_risk(self) -> None:
        summary = _chamber_start_summary(
            datetime(2026, 8, 3, 9, 24),
            datetime(2026, 8, 8, 9, 24),
            datetime(2026, 8, 9, 15, 24),
        )
        texts = [control for control in _walk_controls(summary) if isinstance(control, ft.Text)]
        values = [control.value for control in texts]

        self.assertIn("ENTRADA", values)
        self.assertIn("RETIRADA NOMINAL", values)
        self.assertIn("LIMITE COM TOLERÂNCIA", values)
        self.assertIn("segunda-feira", values)
        self.assertIn("sábado", values)
        self.assertIn("domingo", values)
        self.assertEqual(values.count("FIM DE SEMANA"), 2)
        self.assertTrue(any("equipe poderá realizar a retirada" in value for value in values))
        self.assertEqual(values.count("às 09:24"), 2)
        date_text = texts[values.index("03/08/2026")]
        self.assertEqual(date_text.size, 20)
        self.assertEqual(date_text.weight, ft.FontWeight.BOLD)

    def test_reason_selector_offers_other_and_limits_free_text(self) -> None:
        selector = ReasonSelector(("Manutenção", "Falta de energia"))

        self.assertEqual(
            [option.key for option in selector.dropdown.options],
            ["Manutenção", "Falta de energia", "Outros"],
        )
        self.assertEqual(selector.other.max_length, MAX_REASON_LENGTH)
        self.assertFalse(selector.other.visible)
        selector.dropdown.value = "Outros"
        selector._on_select()
        self.assertTrue(selector.other.visible)
        self.assertFalse(selector.validate())
        selector.other.value = "Interrupção programada"
        self.assertTrue(selector.validate())
        self.assertEqual(selector.value(), "Interrupção programada")

    def test_email_guide_contains_a_complete_configuration_flow(self) -> None:
        guide = " ".join(EMAIL_SETUP_STEPS)

        self.assertGreaterEqual(len(EMAIL_SETUP_STEPS), 7)
        self.assertIn("Configurações", guide)
        self.assertIn("senha de app", guide)
        self.assertIn("porta 587", guide)
        self.assertIn("Testar e-mail", guide)
        self.assertIn("segundo plano", guide)

    def test_email_configuration_opens_provider_models_and_embedded_tutorial(self) -> None:
        async def backup(_event: object | None = None) -> None:
            return None

        class DialogPage:
            def __init__(self) -> None:
                self.dialogs: list[ft.AlertDialog] = []

            def show_dialog(self, dialog: ft.AlertDialog) -> None:
                self.dialogs.append(dialog)

            def pop_dialog(self) -> None:
                return None

            def update(self, *_controls: ft.Control) -> None:
                return None

        settings = build_settings_view(
            database_path=Path("C:/dados/climatetest_manager.db"),
            backup_directory=Path("C:/OneDrive/ClimateTestManager/Backups"),
            notifications_enabled=False,
            notification_status=NotificationStatus(),
            email_settings=EmailSettings(),
            email_recipients=["operador@example.com"],
            system_incidents=[
                SystemIncidentSummary(
                    id=1,
                    category="Falha do software",
                    severity="Médio",
                    description="A tela não abriu durante uma verificação controlada.",
                    immediate_action="O uso foi interrompido e o horário anotado.",
                    status="open",
                    reported_by="Operador Teste (@operador)",
                    reported_at=datetime(2026, 8, 3, 10, 30),
                    corrective_action=None,
                    resolved_by=None,
                    resolved_at=None,
                )
            ],
            theme_mode="light",
            current_user=UserSummary(
                id=1,
                username="operador",
                email="operador@example.com",
                first_name="Operador",
                last_name="Teste",
                role="admin",
                is_active=True,
                onboarding_completed=True,
                last_login_at=None,
            ),
            on_theme_change=lambda _mode: None,
            on_change_password=lambda _old, _new, _confirmation: None,
            on_manage_users=lambda: None,
            on_help=lambda: None,
            on_enable_notifications=lambda: None,
            on_disable_notifications=lambda: None,
            on_test_notification=lambda: None,
            on_save_email_settings=lambda _settings, _password: None,
            on_test_email=lambda: None,
            on_select_profile_photo=lambda _event: backup(),
            on_remove_profile_photo=lambda: None,
            on_open_data_folder=lambda: None,
            on_backup=backup,
            on_configure_backup=backup,
            on_report_system_incident=lambda _category, _severity, _description, _action: None,
            on_resolve_system_incident=lambda _incident_id, _action: None,
            on_refresh=lambda: None,
        )
        email_button = next(
            control
            for control in _walk_controls(settings)
            if isinstance(control, ft.Button) and control.content == "Configurar e-mail"
        )
        page = DialogPage()

        with patch.object(
            ft.Button,
            "page",
            new_callable=PropertyMock,
            return_value=page,
        ):
            email_button.on_click()

        self.assertEqual(len(page.dialogs), 1)
        dialog = page.dialogs[0]
        controls = list(_walk_controls(dialog.content))
        self.assertTrue(dialog.scrollable)
        self.assertTrue(
            any(
                isinstance(control, ft.ExpansionTile)
                and isinstance(control.title, ft.Text)
                and control.title.value == "Como configurar, passo a passo"
                for control in controls
            )
        )
        provider = next(
            control
            for control in controls
            if isinstance(control, ft.Dropdown) and control.label == "Modelo de configuração"
        )
        self.assertEqual(
            [option.key for option in provider.options],
            ["gmail", "microsoft", "other"],
        )

    def test_settings_confirms_destructive_account_and_notification_actions(self) -> None:
        async def backup(_event: object | None = None) -> None:
            return None

        class DialogPage:
            def __init__(self) -> None:
                self.dialogs: list[ft.AlertDialog] = []

            def show_dialog(self, dialog: ft.AlertDialog) -> None:
                self.dialogs.append(dialog)

            def pop_dialog(self) -> None:
                self.dialogs.pop()

        calls: list[str] = []
        settings = build_settings_view(
            database_path=Path("C:/dados/climatetest_manager.db"),
            backup_directory=Path("C:/OneDrive/ClimateTestManager/Backups"),
            notifications_enabled=True,
            notification_status=NotificationStatus(),
            email_settings=EmailSettings(),
            email_recipients=["admin@example.com"],
            system_incidents=[],
            theme_mode="light",
            current_user=UserSummary(
                id=1,
                username="admin",
                email="admin@example.com",
                first_name="Admin",
                last_name="Teste",
                role="admin",
                is_active=True,
                onboarding_completed=True,
                last_login_at=None,
                profile_photo_b64="imagem-de-teste",
            ),
            on_theme_change=lambda _mode: None,
            on_change_password=lambda _old, _new, _confirmation: None,
            on_manage_users=lambda: None,
            on_help=lambda: None,
            on_enable_notifications=lambda: None,
            on_disable_notifications=lambda: calls.append("disable"),
            on_test_notification=lambda: None,
            on_save_email_settings=lambda _settings, _password: None,
            on_test_email=lambda: None,
            on_select_profile_photo=lambda _event: backup(),
            on_remove_profile_photo=lambda: calls.append("photo"),
            on_open_data_folder=lambda: None,
            on_backup=backup,
            on_configure_backup=backup,
            on_report_system_incident=lambda _category, _severity, _description, _action: None,
            on_resolve_system_incident=lambda _incident_id, _action: None,
            on_refresh=lambda: None,
        )
        buttons = {
            control.content: control
            for control in _walk_controls(settings)
            if isinstance(control, ft.Button) and isinstance(control.content, str)
        }
        page = DialogPage()

        with patch.object(
            ft.Button,
            "page",
            new_callable=PropertyMock,
            return_value=page,
        ):
            buttons["Desativar avisos"].on_click()
            self.assertEqual(calls, [])
            page.dialogs[-1].actions[-1].on_click()
            self.assertEqual(calls, ["disable"])

            buttons["Remover foto"].on_click()
            self.assertEqual(calls, ["disable"])
            page.dialogs[-1].actions[-1].on_click()

        self.assertEqual(calls, ["disable", "photo"])

    def test_main_operational_dialogs_share_the_polished_surface(self) -> None:
        class DialogPage:
            def __init__(self) -> None:
                self.dialogs: list[ft.AlertDialog] = []

            def show_dialog(self, dialog: ft.AlertDialog) -> None:
                self.dialogs.append(dialog)

            def pop_dialog(self) -> None:
                return None

            def update(self, *_controls: ft.Control) -> None:
                return None

        user = UserSummary(
            id=1,
            username="operador",
            email="operador@example.com",
            first_name="Operador",
            last_name="Teste",
            role="admin",
            is_active=True,
            onboarding_completed=True,
            last_login_at=None,
        )
        details = DetailsView(
            self.service.get_details(self.test_id),
            on_back=lambda: None,
            on_start_chamber=lambda _value: None,
            on_start_drying=lambda _value: None,
            on_finish=lambda _value: None,
            on_cancel=lambda _reason: None,
            on_edit=lambda: None,
            on_delete=lambda: None,
            on_change_timestamp=lambda _timestamp, _value, _reason: None,
        )
        dashboard = DashboardView(
            self.service.dashboard_summary(),
            self.service.list_dashboard_tests(),
            self.service.resource_statuses(),
            on_new_test=lambda: None,
            on_select=lambda _id: None,
            on_pause_resource=lambda _resource, _reason: None,
            on_resume_resource=lambda _resource: None,
        )
        users = UsersView(
            [user],
            current_user=user,
            on_create=lambda _command: None,
            on_update=lambda _user_id, _command: None,
            on_reset_password=lambda _user_id, _password, _confirmation: None,
        )
        page = DialogPage()

        with patch.object(
            ft.Column,
            "page",
            new_callable=PropertyMock,
            return_value=page,
        ):
            details._show_cancel_dialog()
            dashboard._show_pause_dialog("climate_chamber", "Câmara climática")
            users._show_create_dialog()

        self.assertEqual(len(page.dialogs), 3)
        self.assertTrue(all(dialog.modal for dialog in page.dialogs))
        self.assertTrue(all(dialog.shape.radius == 22 for dialog in page.dialogs))
        self.assertTrue(all(isinstance(dialog.title, ft.Row) for dialog in page.dialogs))

    def test_stage_transition_waits_for_confirmation(self) -> None:
        class DialogPage:
            def __init__(self) -> None:
                self.dialogs: list[ft.AlertDialog] = []

            def show_dialog(self, dialog: ft.AlertDialog) -> None:
                self.dialogs.append(dialog)

            def pop_dialog(self) -> None:
                self.dialogs.pop()

        transitions: list[datetime | None] = []
        view = DetailsView(
            self.service.get_details(self.test_id),
            on_back=lambda: None,
            on_start_chamber=lambda _value: None,
            on_start_drying=transitions.append,
            on_finish=lambda _value: None,
            on_cancel=lambda _reason: None,
            on_edit=lambda: None,
            on_delete=lambda: None,
            on_change_timestamp=lambda _timestamp, _value, _reason: None,
        )
        occurred_at = datetime(2026, 7, 30, 12, 30)
        page = DialogPage()

        with patch.object(
            ft.Column,
            "page",
            new_callable=PropertyMock,
            return_value=page,
        ):
            view._confirm_chamber_exit_to_drying(occurred_at)
            self.assertEqual(transitions, [])
            dialog = page.dialogs[-1]
            self.assertEqual(
                dialog.title.controls[1].controls[0].value,
                "Registrar saída e iniciar a secagem?",
            )
            dialog.actions[-1].on_click()

        self.assertEqual(transitions, [occurred_at])

    def test_builds_history_and_settings(self) -> None:
        async def backup(_event: object | None = None) -> None:
            return None

        history = build_history_view(self.service.list_history(), on_select=lambda _id: None)
        settings = build_settings_view(
            database_path=Path("C:/dados/climatetest_manager.db"),
            backup_directory=Path("C:/OneDrive/ClimateTestManager/Backups"),
            notifications_enabled=False,
            notification_status=NotificationStatus(),
            email_settings=EmailSettings(),
            email_recipients=["operador@example.com"],
            system_incidents=[],
            theme_mode="light",
            current_user=UserSummary(
                id=1,
                username="operador",
                email="operador@example.com",
                first_name="Operador",
                last_name="Teste",
                role="admin",
                is_active=True,
                onboarding_completed=True,
                last_login_at=None,
            ),
            on_theme_change=lambda _mode: None,
            on_change_password=lambda _old, _new, _confirmation: None,
            on_manage_users=lambda: None,
            on_help=lambda: None,
            on_enable_notifications=lambda: None,
            on_disable_notifications=lambda: None,
            on_test_notification=lambda: None,
            on_save_email_settings=lambda _settings, _password: None,
            on_test_email=lambda: None,
            on_select_profile_photo=lambda _event: backup(),
            on_remove_profile_photo=lambda: None,
            on_open_data_folder=lambda: None,
            on_backup=backup,
            on_configure_backup=backup,
            on_report_system_incident=lambda _category, _severity, _description, _action: None,
            on_resolve_system_incident=lambda _incident_id, _action: None,
            on_refresh=lambda: None,
        )

        self.assertIsInstance(history, ft.Column)
        self.assertIsInstance(settings, ft.Column)
        settings_text = " ".join(
            control.value for control in _walk_controls(settings) if isinstance(control, ft.Text)
        )
        self.assertIn("Destinatários automáticos: operador@example.com", settings_text)
        self.assertIn("ABNT NBR ISO/IEC 17025:2017", settings_text)
        self.assertIn("ABNT NBR IEC 60079-0:2020", settings_text)

    def test_builds_internal_agenda_from_active_deadlines(self) -> None:
        self.service.start_chamber(self.test_id)
        agenda = AgendaView(
            self.service.list_agenda_events(),
            on_select=lambda _id: None,
            today_provider=lambda: self.now.date(),
        )

        self.assertIsInstance(agenda.root, ft.Column)
        self.assertEqual(len(agenda._events), 2)

    def test_dashboard_builds_active_rows_with_compact_progress(self) -> None:
        self.service.start_chamber(self.test_id)
        dashboard = DashboardView(
            self.service.dashboard_summary(),
            self.service.list_dashboard_tests(),
            self.service.resource_statuses(),
            on_new_test=lambda: None,
            on_select=lambda _id: None,
            on_pause_resource=lambda _resource, _reason: None,
            on_resume_resource=lambda _resource: None,
        )

        self.assertIsInstance(dashboard.root, ft.Column)
        self.assertEqual(
            self.service.list_dashboard_tests()[0].situation,
            "Na Câmara",
        )
        self.assertTrue(all(card.on_click is not None for card in dashboard.metrics.controls))
        self.assertIsInstance(dashboard.metrics, ft.ResponsiveRow)
        self.assertEqual(dashboard.metrics.controls[0].col["sm"], 6)
        dashboard._active_filter = "in_progress"
        dashboard._refresh_filter(update=False)
        self.assertEqual(dashboard.results_title.value, "Filtro: em andamento")

    def test_wrapping_rows_never_receive_expanded_children(self) -> None:
        """Evita os blocos cinza gerados pelo Flutter nessa combinação inválida."""

        user = UserSummary(
            id=1,
            username="operador",
            email="operador@example.com",
            first_name="Operador",
            last_name="Teste",
            role="admin",
            is_active=True,
            onboarding_completed=True,
            last_login_at=None,
        )
        details = DetailsView(
            self.service.get_details(self.test_id),
            on_back=lambda: None,
            on_start_chamber=lambda _value: None,
            on_start_drying=lambda _value: None,
            on_finish=lambda _value: None,
            on_cancel=lambda _reason: None,
            on_edit=lambda: None,
            on_delete=lambda: None,
            on_change_timestamp=lambda _timestamp, _value, _reason: None,
        )
        dashboard = DashboardView(
            self.service.dashboard_summary(),
            self.service.list_dashboard_tests(),
            self.service.resource_statuses(),
            on_new_test=lambda: None,
            on_select=lambda _id: None,
            on_pause_resource=lambda _resource, _reason: None,
            on_resume_resource=lambda _resource: None,
        )
        history = build_history_view(self.service.list_history(), on_select=lambda _id: None)
        users = UsersView(
            [user],
            current_user=user,
            on_create=lambda _command: None,
            on_update=lambda _user_id, _command: None,
            on_reset_password=lambda _user_id, _password, _confirmation: None,
        )
        self.service.start_chamber(self.test_id)
        agenda = AgendaView(
            self.service.list_agenda_events(),
            on_select=lambda _id: None,
            today_provider=lambda: self.now.date(),
        )
        new_test = NewTestView(
            on_cancel=lambda: None,
            on_save=lambda _command: None,
        )

        for root in (
            details.root,
            dashboard.root,
            history,
            users.root,
            agenda.root,
            new_test.root,
        ):
            for control in _walk_controls(root):
                if isinstance(control, ft.Row) and control.wrap:
                    expanded_children = [child for child in control.controls if bool(child.expand)]
                    self.assertEqual(
                        expanded_children,
                        [],
                        "Row com wrap não pode receber filho com expand; "
                        "o Flutter renderiza um bloco cinza.",
                    )
                if isinstance(control, ft.ResponsiveRow):
                    expanded_children = [child for child in control.controls if bool(child.expand)]
                    self.assertEqual(
                        expanded_children,
                        [],
                        "ResponsiveRow não pode receber filho com expand; "
                        "o Flutter pode deixar toda a seção em branco.",
                    )

    def test_details_uses_two_balanced_phase_cards_and_full_width_history(self) -> None:
        view = DetailsView(
            self.service.get_details(self.test_id),
            on_back=lambda: None,
            on_start_chamber=lambda _value: None,
            on_start_drying=lambda _value: None,
            on_finish=lambda _value: None,
            on_cancel=lambda _reason: None,
            on_edit=lambda: None,
            on_delete=lambda: None,
            on_change_timestamp=lambda _timestamp, _value, _reason: None,
        )

        self.assertEqual(
            view.root.horizontal_alignment,
            ft.CrossAxisAlignment.STRETCH,
        )
        phase_panel = view._phase_panel()
        phase_layout = phase_panel.content.controls[-1]
        self.assertIsInstance(phase_layout, ft.ResponsiveRow)
        self.assertEqual(len(phase_layout.controls), 2)
        self.assertTrue(all(card.col["lg"] == 6 for card in phase_layout.controls))

        history_panel = view._history_panel()
        self.assertIsNotNone(history_panel.border)
        self.assertEqual(
            history_panel.content.horizontal_alignment,
            ft.CrossAxisAlignment.STRETCH,
        )

    def test_user_dialog_grid_is_compact_and_responsive(self) -> None:
        user = UserSummary(
            id=1,
            username="operador",
            email="operador@example.com",
            first_name="Operador",
            last_name="Teste",
            role="admin",
            is_active=True,
            onboarding_completed=True,
            last_login_at=None,
        )
        view = UsersView(
            [user],
            current_user=user,
            on_create=lambda _command: None,
            on_update=lambda _user_id, _command: None,
            on_reset_password=lambda _user_id, _password, _confirmation: None,
        )
        fields = view._identity_fields(user)
        role = ft.Dropdown(value="admin")
        grid = view._identity_grid(*fields, role)

        self.assertIsInstance(grid, ft.ResponsiveRow)
        self.assertEqual(len(grid.controls), 5)
        self.assertEqual(grid.controls[0].col["sm"], 6)
        self.assertEqual(grid.controls[2].col["sm"], 7)
        self.assertEqual(grid.controls[-1].col["xs"], 12)

    def test_resource_buttons_keep_label_on_one_line(self) -> None:
        dashboard = DashboardView(
            self.service.dashboard_summary(),
            self.service.list_dashboard_tests(),
            self.service.resource_statuses(),
            on_new_test=lambda: None,
            on_select=lambda _id: None,
            on_pause_resource=lambda _resource, _reason: None,
            on_resume_resource=lambda _resource: None,
        )
        card = dashboard._resource_card(
            self.service.resource_statuses()[0],
            lambda _resource: None,
        )
        action_container = card.content.controls[1]
        button = action_container.content

        self.assertEqual(action_container.col["md"], 4)
        self.assertIsInstance(button, ft.Button)
        self.assertEqual(button.width, 124)
        self.assertIsInstance(button.content, ft.Text)
        self.assertTrue(button.content.no_wrap)
        self.assertIsNotNone(button.on_click)

    def test_profile_photo_uses_high_quality_antialiasing(self) -> None:
        user = UserSummary(
            id=1,
            username="operador",
            email="operador@example.com",
            first_name="Operador",
            last_name="Teste",
            role="admin",
            is_active=True,
            onboarding_completed=True,
            last_login_at=None,
            profile_photo_b64="aW1hZ2Vt",
        )
        avatar = user_avatar(user, size=42)

        self.assertEqual(avatar.clip_behavior, ft.ClipBehavior.ANTI_ALIAS)
        self.assertIsInstance(avatar.content, ft.Image)
        self.assertTrue(avatar.content.anti_alias)
        self.assertEqual(avatar.content.filter_quality, ft.FilterQuality.HIGH)
        self.assertEqual(avatar.content.cache_width, 126)


if __name__ == "__main__":
    unittest.main()
