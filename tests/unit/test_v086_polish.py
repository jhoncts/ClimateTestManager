import flet as ft

from climatetest_manager import v086_polish, v086_runtime


def _walk(control: ft.Control):
    yield control
    child = getattr(control, "content", None)
    if isinstance(child, ft.Control):
        yield from _walk(child)
    for item in getattr(control, "controls", ()) or ():
        if isinstance(item, ft.Control):
            yield from _walk(item)


def _texts(control: ft.Control) -> list[str]:
    return [str(item.value or "") for item in _walk(control) if isinstance(item, ft.Text)]


def _patched_view(monkeypatch):
    cls = v086_runtime.V086NewTestView
    monkeypatch.setattr(cls, "_thermal_panel", v086_polish._integrated_thermal_panel)
    monkeypatch.setattr(cls, "_build", v086_polish._build_semantic)
    monkeypatch.setattr(cls, "_sync_top_card_height", v086_polish._sync_semantic_layout)
    monkeypatch.setattr(cls, "_on_cold_change", v086_polish._cold_change_semantic)
    return cls(on_cancel=lambda: None, on_save=lambda *_args: None)


def test_new_test_layout_groups_context_and_thermal_configuration(monkeypatch) -> None:
    view = _patched_view(monkeypatch)
    texts = _texts(view.root)

    assert "Identificação" in texts
    assert "Configuração térmica" in texts
    assert "Informações complementares" in texts
    assert "26.9 - Resistência térmica ao frio" in texts
    assert "Após o calor" not in texts

    workspace = view.root.controls[2]
    assert isinstance(workspace, ft.ResponsiveRow)
    assert len(workspace.controls) == 2
    assert workspace.controls[0].col == {"xs": 12, "lg": 5}
    assert workspace.controls[1].col == {"xs": 12, "lg": 7}
    assert view._identity_panel_control.height is None
    assert view._thermal_panel_control.height is None


def test_cold_section_is_compact_and_expands_only_when_selected(monkeypatch) -> None:
    view = _patched_view(monkeypatch)

    assert view.cold_planned.label == "Realizar ensaio"
    assert view._cold_fields.visible is False
    assert view._cold_panel_control is not None

    view.cold_planned.value = True
    view._on_cold_change(None)
    assert view._cold_fields.visible is True
    assert view._cold_preview.size == 11
    assert view.minimum_ambient_service_temperature.height == 46


def test_small_auxiliary_texts_are_promoted_for_legibility(monkeypatch) -> None:
    view = _patched_view(monkeypatch)
    thermal = view._thermal_panel_control
    small_texts = [
        item
        for item in _walk(thermal)
        if isinstance(item, ft.Text) and isinstance(item.size, (int, float)) and item.size < 9.5
    ]
    assert small_texts == []
