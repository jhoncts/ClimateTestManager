"""Regressões das telas críticas estabilizadas na rodada 5."""

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import flet as ft

from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.climate_tests import ClimateTestRepository
from climatetest_manager.round5_runtime import BUILD_REVISION, StableDetailsView, StableNewTestView
from climatetest_manager.services.climate_tests import ClimateTestService, CreateClimateTestCommand


def _walk(control: ft.Control):
    yield control
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk(content)
    for child in getattr(control, "controls", ()) or ():
        if isinstance(child, ft.Control):
            yield from _walk(child)


def _has_revision(root: ft.Control) -> bool:
    return any(
        isinstance(control, ft.Text) and BUILD_REVISION in (control.value or "")
        for control in _walk(root)
    )


class Round5RuntimeTests(unittest.TestCase):
    def test_new_test_has_one_scroll_owner_and_no_list_view_root(self) -> None:
        view = StableNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)

        self.assertIsInstance(view.root, ft.Column)
        self.assertEqual(view.root.scroll, ft.ScrollMode.AUTO)
        self.assertNotIsInstance(view.root, ft.ListView)
        self.assertTrue(_has_revision(view.root))

    def test_details_uses_simple_scroll_root_and_keeps_operational_panels(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            engine = initialize_database(Path(temporary_directory) / "round5.db")
            try:
                repository = ClimateTestRepository(create_session_factory(engine))
                service = ClimateTestService(
                    repository,
                    now_provider=lambda: datetime(2026, 8, 12, 15, 0),
                )
                test_id = service.create(
                    CreateClimateTestCommand(
                        client="Cliente R5",
                        process_number="26123.1",
                        product="Luminária",
                        epl="Gb",
                        tamb_max_c="40",
                        delta_t_max_k="35",
                        selected_option="B",
                    )
                )
                view = StableDetailsView(
                    service.get_details(test_id),
                    on_back=lambda: None,
                    on_start_chamber=lambda _value: None,
                    on_start_drying=lambda _value: None,
                    on_finish=lambda _value: None,
                    on_cancel=lambda _reason: None,
                    on_edit=lambda: None,
                    on_delete=lambda: None,
                    on_change_timestamp=lambda _timestamp, _value, _reason: None,
                )

                self.assertIsInstance(view.root, ft.Column)
                self.assertEqual(view.root.scroll, ft.ScrollMode.AUTO)
                self.assertGreaterEqual(len(view.root.controls), 7)
                self.assertTrue(_has_revision(view.root))
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
