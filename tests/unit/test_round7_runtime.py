"""Regressões da R7: layout clean e seleção direta na Tabela 17."""

import unittest
from decimal import Decimal

import flet as ft

from climatetest_manager.round7_runtime import TABLE17_MODE, CleanNewTestView
from climatetest_manager.ui.components.table17_interactive import ts_band_label
from climatetest_manager.ui.responsive import LayoutProfile


def walk(control: ft.Control):
    yield control
    child = getattr(control, "content", None)
    if isinstance(child, ft.Control):
        yield from walk(child)
    for item in getattr(control, "controls", ()) or ():
        if isinstance(item, ft.Control):
            yield from walk(item)


def texts(control: ft.Control) -> list[str]:
    values: list[str] = []
    for item in walk(control):
        if isinstance(item, ft.Text):
            values.append(str(item.value or ""))
        elif isinstance(item, ft.Button) and isinstance(item.content, str):
            values.append(item.content)
    return values


class Round7RuntimeTests(unittest.TestCase):
    def test_new_test_has_one_vertical_scroll_and_no_revision_banner(self) -> None:
        view = CleanNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
        self.assertIsInstance(view.root, ft.Column)
        self.assertEqual(view.root.scroll, ft.ScrollMode.AUTO)
        content = " ".join(texts(view.root))
        self.assertNotIn("Interface refinada", content)
        self.assertNotIn("Interface estável", content)
        self.assertEqual(content.count("Condição que será aplicada"), 1)
        self.assertIn("Visualização simples", content)
        self.assertIn("Visualização avançada", content)

    def test_table_mode_requires_ts_epl_and_condition(self) -> None:
        view = CleanNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
        view.mode_group.value = TABLE17_MODE
        view._on_mode_change()
        self.assertTrue(view.save_button.disabled)
        view.service_temperature.value = "81"
        view._recalculate()
        self.assertTrue(view.save_button.disabled)
        view._select_table_epl("Gb")
        self.assertEqual(view.epl.value, "Gb")
        self.assertTrue(view.save_button.disabled)
        view._select_table_option("B")
        self.assertFalse(view.save_button.disabled)
        self.assertEqual(view.option_group.value, "B")
        self.assertEqual(view._condition.rule_id, "G1-HIGH-B")

    def test_table_uses_correct_ts_ranges(self) -> None:
        self.assertEqual(ts_band_label("Gb", Decimal("81")), "Ts ≥ 75 °C")
        self.assertEqual(ts_band_label("Gc", Decimal("81")), "80 °C < Ts ≤ 85 °C")

    def test_normal_notebook_width_keeps_sidebar_labels(self) -> None:
        self.assertEqual(LayoutProfile.from_width(1100).mode, "regular")
        self.assertFalse(LayoutProfile.from_width(1100).compact_navigation)
        self.assertEqual(LayoutProfile.from_width(920).mode, "regular")
        self.assertFalse(LayoutProfile.from_width(920).compact_navigation)


if __name__ == "__main__":
    unittest.main()
