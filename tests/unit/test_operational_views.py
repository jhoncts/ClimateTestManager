"""Testes de montagem das novas telas operacionais."""

import asyncio
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import flet as ft

from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.climate_tests import ClimateTestRepository, NotificationStatus
from climatetest_manager.services.climate_tests import ClimateTestService, CreateClimateTestCommand
from climatetest_manager.ui.views.agenda import AgendaView
from climatetest_manager.ui.views.dashboard import DashboardView
from climatetest_manager.ui.views.history import build_history_view
from climatetest_manager.ui.views.settings import build_settings_view
from climatetest_manager.ui.views.test_details import TestDetailsView as DetailsView
from climatetest_manager.ui.views.tests_list import TestsListView as ListView


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
            on_calendar=lambda: None,
            on_change_chamber_start=lambda _value, _reason: None,
        )
        view.date.value = "22/07/2026"
        view.time.value = "07:45"
        view._manual(starts.append)

        self.assertIsInstance(view.root, ft.Column)
        self.assertEqual(starts, [datetime(2026, 7, 22, 7, 45)])
        self.assertTrue(callable(view._on_cancel))

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
            on_calendar=lambda: None,
            on_change_chamber_start=lambda _value, _reason: None,
        )
        view.date.value = "06072026123"
        view.date.on_change()
        view.time.value = "143099"
        view.time.on_change()

        self.assertEqual(view.date.value, "06/07/2026")
        self.assertEqual(view.time.value, "14:30")
        self.assertEqual(view.date.max_length, 10)
        self.assertEqual(view.time.max_length, 5)

    def test_builds_history_and_settings(self) -> None:
        async def backup(_event: object | None = None) -> None:
            return None

        history = build_history_view(self.service.list_history(), on_select=lambda _id: None)
        settings = build_settings_view(
            database_path=Path("C:/dados/climatetest_manager.db"),
            notifications_enabled=False,
            notification_status=NotificationStatus(),
            theme_mode="light",
            on_theme_change=lambda _mode: None,
            on_enable_notifications=lambda: None,
            on_disable_notifications=lambda: None,
            on_test_notification=lambda: None,
            on_open_data_folder=lambda: None,
            on_backup=backup,
        )

        self.assertIsInstance(history, ft.Column)
        self.assertIsInstance(settings, ft.Column)

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


if __name__ == "__main__":
    unittest.main()
