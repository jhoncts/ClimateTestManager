"""Regressões das telas críticas observadas no Windows real."""

import unittest
from datetime import datetime

import flet as ft

from climatetest_manager.repositories.climate_tests import SystemIncidentSummary
from climatetest_manager.round4_runtime import SafeNewTestView, _safe_incident_panel, _walk


class Round4RuntimeTests(unittest.TestCase):
    def test_new_test_uses_single_stable_scroll_root(self) -> None:
        view = SafeNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)

        self.assertIsInstance(view.root, ft.ListView)
        self.assertTrue(view.root.expand)
        self.assertFalse(
            any(
                isinstance(control, ft.ListView)
                for control in _walk(view.root)
                if control is not view.root
            )
        )

    def test_blank_submit_marks_required_identity_fields(self) -> None:
        view = SafeNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
        view.client.value = ""
        view.process_number.value = ""
        view.product.value = ""
        view.sample_quantity.value = ""
        view.save_button.disabled = False

        view._submit()

        self.assertEqual(view.client.error, "Campo obrigatório.")
        self.assertEqual(view.process_number.error, "Campo obrigatório.")
        self.assertEqual(view.product.error, "Campo obrigatório.")
        self.assertEqual(view.sample_quantity.error, "Campo obrigatório.")
        self.assertTrue(view.error_banner.visible)

    def test_incident_panel_does_not_create_nested_scroll_area(self) -> None:
        incident = SystemIncidentSummary(
            id=1,
            category="Falha de software",
            severity="Alta",
            description="A interface deixou de apresentar parte do conteúdo.",
            immediate_action="Uso interrompido e registros conferidos.",
            status="open",
            reported_by="Administrador",
            reported_at=datetime(2026, 8, 12, 14, 0),
            corrective_action=None,
            resolved_by=None,
            resolved_at=None,
        )
        panel = _safe_incident_panel(
            system_incidents=[incident],
            on_report_system_incident=lambda *_args: None,
            on_resolve_system_incident=lambda *_args: None,
            on_refresh=lambda: None,
        )

        self.assertIsInstance(panel, ft.Column)
        self.assertFalse(any(isinstance(control, ft.ListView) for control in _walk(panel)))
        self.assertTrue(
            any(
                isinstance(control, ft.Text)
                and control.value == "Falhas do sistema e ações corretivas"
                for control in _walk(panel)
            )
        )


if __name__ == "__main__":
    unittest.main()
