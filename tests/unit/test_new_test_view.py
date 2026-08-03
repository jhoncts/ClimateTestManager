"""Testes rápidos do estado do formulário Flet."""

import unittest

import flet as ft

from climatetest_manager.domain.enums import ConditionInputMode
from climatetest_manager.services.climate_tests import CreateClimateTestCommand
from climatetest_manager.ui.views.new_test import NewTestView


class NewTestViewTests(unittest.TestCase):
    def test_ts_75_enables_b_and_uses_upper_band(self) -> None:
        view = NewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
        view.epl.value = "Gb"
        view.tamb.value = "40"
        view.delta_t.value = "35"

        view._recalculate()

        self.assertEqual(view.ts_value.value, "Ts = 75 °C")
        self.assertFalse(view.option_b.disabled)
        self.assertEqual(view.chamber_temperature.value, "95 ± 2 °C")
        self.assertEqual(view.chamber_duration.value, "336 h (+30 h)")
        self.assertEqual(
            view.chamber_duration_detail.value,
            "14 dias nominais • limite: 15 dias e 6 horas",
        )

    def test_display_preserves_trailing_zeros_of_integer_values(self) -> None:
        view = NewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
        view.epl.value = "Gb"
        view.tamb.value = "40"
        view.delta_t.value = "100"
        view.option_group.value = "B"

        view._recalculate()

        self.assertEqual(view.ts_value.value, "Ts = 140 °C")
        self.assertEqual(view.chamber_temperature.value, "90 ± 2 °C")
        self.assertEqual(view.chamber_humidity.value, "90 ± 5 % UR")
        self.assertEqual(view.drying_temperature.value, "160 ± 2 °C")

    def test_blank_tamb_uses_positive_40_celsius(self) -> None:
        view = NewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
        view.epl.value = "Gb"
        view.tamb.value = ""
        view.delta_t.value = "35"

        view._recalculate()

        self.assertEqual(view.ts_value.value, "Ts = 75 °C")
        self.assertTrue(view.tamb_assumption.visible)
        self.assertFalse(view.save_button.disabled)

    def test_numeric_fields_remove_letters_and_normalize_decimal_separator(self) -> None:
        view = NewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
        view.tamb.value = "-20.5 abc"
        view.delta_t.value = "35.75 K"

        view._on_tamb_change()
        view._on_delta_t_change()

        self.assertEqual(view.tamb.value, "-20,5")
        self.assertEqual(view.delta_t.value, "35,75")

    def test_process_field_is_free_text_with_updated_example_and_length(self) -> None:
        view = NewTestView(on_cancel=lambda: None, on_save=lambda _command: None)

        self.assertEqual(view.process_number.hint_text, "Ex.: 26123.1")
        self.assertEqual(view.process_number.max_length, 10)
        self.assertEqual(view.process_number.counter, "")
        self.assertFalse(hasattr(view, "ex_marking"))

    def test_sample_quantity_can_be_cleared_and_replaced(self) -> None:
        view = NewTestView(on_cancel=lambda: None, on_save=lambda _command: None)

        self.assertEqual(view.sample_quantity.value, "1")
        view.sample_quantity.value = ""
        view._on_sample_quantity_change()
        self.assertEqual(view.sample_quantity.value, "")

        view.sample_quantity.value = "2"
        view._on_sample_quantity_change()
        self.assertEqual(view.sample_quantity.value, "2")

    def test_sample_quantity_removes_non_numeric_content(
        self,
    ) -> None:
        view = NewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
        view.sample_quantity.value = "1a2"

        view._on_sample_quantity_change()

        self.assertEqual(view.sample_quantity.value, "12")
        self.assertIsNone(view.sample_quantity.input_filter)
        self.assertEqual(view.sample_quantity.max_length, 2)

    def test_sample_quantity_removes_leading_zero(self) -> None:
        view = NewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
        view.sample_quantity.value = "01"

        view._on_sample_quantity_change()

        self.assertEqual(view.sample_quantity.value, "1")

    def test_draft_restores_form_after_navigation(self) -> None:
        view = NewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
        view.client.value = "Cliente temporário"
        view.process_number.value = "26123.9"
        view.product.value = "Produto temporário"
        view.sample_quantity.value = "4"

        restored = NewTestView(
            on_cancel=lambda: None,
            on_save=lambda _command: None,
            draft=view.snapshot_draft(),
        )

        self.assertEqual(restored.client.value, "Cliente temporário")
        self.assertEqual(restored.process_number.value, "26123.9")
        self.assertEqual(restored.product.value, "Produto temporário")
        self.assertEqual(restored.sample_quantity.value, "4")

    def test_submit_passes_filled_command_to_callback(self) -> None:
        received: list[CreateClimateTestCommand] = []
        view = NewTestView(on_cancel=lambda: None, on_save=received.append)
        view.client.value = "Cliente"
        view.process_number.value = "Processo"
        view.product.value = "Produto"
        view.epl.value = "Gc"
        view.tamb.value = "50"
        view.delta_t.value = "30"
        view._recalculate()

        view._submit()

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].selected_option, "A")

    def test_submit_preserves_direct_configuration_mode(self) -> None:
        received: list[CreateClimateTestCommand] = []
        view = NewTestView(on_cancel=lambda: None, on_save=received.append)
        view.mode_group.value = ConditionInputMode.DIRECT_CONFIGURATION.value
        view._on_mode_change()
        view.client.value = "Cliente"
        view.process_number.value = "26128.1"
        view.product.value = "Produto"
        view.epl.value = None
        view.manual_chamber_temperature.value = "80"
        view.manual_chamber_humidity.value = "90"
        view.manual_chamber_duration.value = "672"
        view._recalculate()

        view._submit()

        self.assertEqual(len(received), 1)
        self.assertEqual(
            received[0].input_mode,
            ConditionInputMode.DIRECT_CONFIGURATION.value,
        )
        self.assertEqual(received[0].selected_option, "")
        self.assertEqual(received[0].manual_chamber_humidity_percent, "90")

    def test_offers_only_three_condition_definition_modes(self) -> None:
        view = NewTestView(on_cancel=lambda: None, on_save=lambda _command: None)

        radios = view.mode_group.content.controls

        self.assertEqual(len(radios), 3)
        self.assertEqual(radios[-1].label, "Personalizado")
        self.assertIsInstance(view.mode_group.content, ft.Row)
        self.assertTrue(view.mode_group.content.wrap)

    def test_uses_full_width_and_balanced_preview_cards(self) -> None:
        view = NewTestView(on_cancel=lambda: None, on_save=lambda _command: None)

        self.assertEqual(
            view.root.horizontal_alignment,
            ft.CrossAxisAlignment.STRETCH,
        )
        self.assertIsNotNone(view.result_panel.border)
        result_layouts = [
            control
            for control in view.result_panel.content.controls
            if isinstance(control, ft.ResponsiveRow)
        ]
        phase_layout = result_layouts[-1]
        self.assertEqual(len(phase_layout.controls), 2)
        self.assertEqual(phase_layout.controls[0].col["lg"], 7)
        self.assertEqual(phase_layout.controls[1].col["lg"], 5)

    def test_permanence_detail_wraps_instead_of_using_ellipsis(self) -> None:
        view = NewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
        view.epl.value = "Gb"
        view.tamb.value = "40"
        view.delta_t.value = "35"
        view._recalculate()

        self.assertFalse(view.chamber_duration_detail.no_wrap)
        self.assertIsNone(view.chamber_duration_detail.max_lines)
        self.assertNotEqual(
            view.chamber_duration_detail.overflow,
            ft.TextOverflow.ELLIPSIS,
        )
        self.assertEqual(
            view.chamber_duration_detail.value,
            "14 dias nominais • limite: 15 dias e 6 horas",
        )

    def test_custom_mode_accepts_long_duration_but_rejects_temperature_over_100(self) -> None:
        view = NewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
        view.mode_group.value = ConditionInputMode.DIRECT_CONFIGURATION.value
        view._on_mode_change()
        view.manual_chamber_temperature.value = "101"
        view.manual_chamber_humidity.value = "90"
        view.manual_chamber_duration.value = "100000"

        view._recalculate()

        self.assertTrue(view.save_button.disabled)
        self.assertIn("0 e 100", view.option_help.value)


if __name__ == "__main__":
    unittest.main()
