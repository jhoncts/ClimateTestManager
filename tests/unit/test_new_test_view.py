"""Testes rápidos do estado do formulário Flet."""

import unittest

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

    def test_submit_passes_filled_command_to_callback(self) -> None:
        received: list[CreateClimateTestCommand] = []
        view = NewTestView(on_cancel=lambda: None, on_save=received.append)
        view.client.value = "Cliente"
        view.process_number.value = "Processo"
        view.product.value = "Produto"
        view.ex_marking.value = "Ex db"
        view.epl.value = "Gc"
        view.tamb.value = "50"
        view.delta_t.value = "30"
        view._recalculate()

        view._submit()

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].selected_option, "A")


if __name__ == "__main__":
    unittest.main()
