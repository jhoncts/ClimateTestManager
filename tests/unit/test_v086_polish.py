import flet as ft

from climatetest_manager import v086_polish
from climatetest_manager.v086_runtime import V086NewTestView


def _walk(control: ft.Control):
    yield control
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk(content)
    for child in getattr(control, "controls", ()) or ():
        if isinstance(child, ft.Control):
            yield from _walk(child)


def _texts(control: ft.Control) -> list[str]:
    return [str(item.value or "") for item in _walk(control) if isinstance(item, ft.Text)]


def test_post_heat_planning_is_integrated_into_thermal_card() -> None:
    v086_polish.install()
    view = V086NewTestView(
        on_cancel=lambda: None,
        on_save=lambda _command, _planned, _temperature: None,
    )

    assert isinstance(view.root, ft.Column)
    assert len(view.root.controls) == 6
    top_cards = view.root.controls[2]
    assert isinstance(top_cards, ft.Row)
    thermal = top_cards.controls[1]
    assert thermal is view._thermal_panel_control
    texts = _texts(thermal)
    assert "Configuração térmica" in texts
    assert "Após o calor" in texts
    assert "Etapa posterior ao calor" not in _texts(view.root)
    assert view._thermal_panel_control.height > view._identity_panel_control.height

    collapsed_height = view._thermal_panel_control.height
    view.cold_planned.value = True
    view._on_cold_change()
    assert view._cold_fields.visible is True
    assert view._thermal_panel_control.height > collapsed_height
