"""Regressões da R6: refinamento sem retornar às telas vazias."""

import unittest
from datetime import UTC, datetime

import flet as ft

from climatetest_manager.config import EmailSettings
from climatetest_manager.repositories.climate_tests import SystemIncidentSummary
from climatetest_manager.round6_compat import navigation_surface
from climatetest_manager.round6_runtime import (
    BUILD_REVISION,
    RefinedNewTestView,
    _compact_incident_panel,
    apply_interaction_polish,
)
from climatetest_manager.round6_table17 import R6NewTestView
from climatetest_manager.ui.theme import AppColors


def _walk(control: ft.Control):
    yield control
    child = getattr(control, "content", None)
    if isinstance(child, ft.Control):
        yield from _walk(child)
    for item in getattr(control, "controls", ()) or ():
        if isinstance(item, ft.Control):
            yield from _walk(item)


def _texts(root: ft.Control) -> list[str]:
    return [
        control.value or ""
        for control in _walk(root)
        if isinstance(control, ft.Text)
    ]


class Round6RuntimeTests(unittest.TestCase):
    def test_new_test_keeps_single_page_scroll_owner_and_compact_two_columns(self) -> None:
        view = R6NewTestView(on_cancel=lambda: None, on_save=lambda _command: None)

        self.assertIsInstance(view.root, ft.Column)
        self.assertEqual(view.root.scroll, ft.ScrollMode.AUTO)
        scrollables = [
            control
            for control in _walk(view.root)
            if isinstance(control, ft.ScrollableControl)
        ]
        self.assertEqual(scrollables, [view.root])
        all_text = _texts(view.root)
        self.assertTrue(any(BUILD_REVISION in value for value in all_text))
        self.assertIn("Tabela 17 — alternativa aplicada", all_text)
        self.assertIn("Alternativa A", all_text)
        self.assertIn("Alternativa B", all_text)
        self.assertIn("Visualizar Tabela 17 completa", all_text)

    def test_table17_highlight_tracks_selected_option_without_new_scroll_region(self) -> None:
        view = RefinedNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
        view.option_group.value = "A"
        view._refresh_table17_preview(update=False)

        self.assertEqual(view._table17_a_status.value, "Aplicada ao ensaio")
        self.assertNotEqual(view._table17_b_status.value, "Aplicada ao ensaio")

    def test_sidebar_count_is_inside_navigation_surface_not_overflow_badge(self) -> None:
        surface = navigation_surface(
            label="Notificações",
            icon=ft.Icons.NOTIFICATIONS_OUTLINED,
            selected=False,
            compact=False,
            icon_size=20,
            on_click=lambda: None,
            badge_count=7,
        )

        self.assertIsNone(surface.badge)
        self.assertIn("7", _texts(surface))
        self.assertEqual(surface.mouse_cursor, ft.MouseCursor.CLICK)

    def test_filled_buttons_gain_overlay_and_pointer_without_losing_fill(self) -> None:
        button = ft.Button(
            content="Salvar",
            bgcolor=AppColors.PRIMARY,
            color=AppColors.WHITE,
            style=ft.ButtonStyle(elevation=1),
        )
        original_fill = button.bgcolor

        apply_interaction_polish(button)

        self.assertEqual(button.bgcolor, original_fill)
        self.assertIsNotNone(button.style)
        self.assertIsNotNone(button.style.overlay_color)
        self.assertIsNotNone(button.style.mouse_cursor)

    def test_settings_uses_log_button_instead_of_rendering_all_incidents_inline(self) -> None:
        incident = SystemIncidentSummary(
            id=25,
            reason_code="database",
            category="Banco de dados, backup ou restauração",
            severity="Crítica",
            description="Falha de teste que deve aparecer somente dentro do log.",
            immediate_action="Registro para avaliação.",
            status="open",
            reported_by="Operador",
            reported_at=datetime(2026, 8, 13, 10, 30, tzinfo=UTC),
            corrective_action=None,
            resolved_by=None,
            resolved_at=None,
        )
        panel = _compact_incident_panel(
            system_incidents=[incident],
            on_report_system_incident=lambda *_args: None,
            on_resolve_system_incident=lambda *_args: None,
            on_refresh=lambda: None,
            email_settings=EmailSettings(),
        )
        all_text = _texts(panel)

        self.assertTrue(any(value.startswith("Log de falhas") for value in all_text))
        self.assertNotIn(incident.description, all_text)
        self.assertIn("1 não resolvida(s)", all_text)


if __name__ == "__main__":
    unittest.main()
