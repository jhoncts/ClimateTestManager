"""Regressões descobertas no teste de aceitação real do instalador."""

from climatetest_manager.ui.views.final_new_test import FinalNewTestView


def test_direct_ts_can_be_cleared_completely_before_typing_another_value() -> None:
    view = FinalNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)

    assert view.service_temperature.input_filter is None

    view.service_temperature.value = "64"
    view._on_condition_input_change()
    assert view.service_temperature.value == "64"

    view.service_temperature.value = ""
    view._on_condition_input_change()
    assert view.service_temperature.value == ""

    view.service_temperature.value = "69a,5x"
    view._on_condition_input_change()
    assert view.service_temperature.value == "69,5"


def test_all_live_condition_fields_allow_the_empty_editing_state() -> None:
    view = FinalNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)

    fields = (
        view.service_temperature,
        view.manual_chamber_temperature,
        view.manual_chamber_humidity,
        view.manual_chamber_duration,
        view.manual_drying_temperature,
        view.manual_drying_duration,
    )
    assert all(field.input_filter is None for field in fields)

    for field in fields:
        field.value = ""
    view._on_condition_input_change()

    assert all(field.value == "" for field in fields)
