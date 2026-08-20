from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import flet as ft

from climatetest_manager.domain.cold_flow import ColdTemperatureRange
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.v086_schedule import (
    _project_climatic_stages,
    _prune_duplicate_cancel,
    _schedule_summary,
    _weekend_events,
)


def _details(*, drying_required: bool = True):
    return SimpleNamespace(
        chamber_duration_hours=672,
        chamber_duration_tolerance_hours=30,
        chamber_temperature_c=Decimal("90"),
        chamber_humidity_percent=Decimal("90"),
        drying_required=drying_required,
        drying_duration_hours=24 if drying_required else None,
        drying_duration_tolerance_hours=0 if drying_required else None,
        drying_temperature_c=Decimal("80") if drying_required else None,
    )


def _workflow(*, cold_planned: bool = True):
    return SimpleNamespace(
        cold_planned=cold_planned,
        temperature_range=ColdTemperatureRange(
            minimum_c=Decimal("-30"),
            maximum_c=Decimal("-25"),
        ),
    )


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


def test_projects_heat_drying_conditioning_and_cold_in_sequence() -> None:
    entry = datetime(2026, 8, 20, 8, 55)

    stages = _project_climatic_stages(_details(), _workflow(), entry)

    assert [stage.key for stage in stages] == ["heat", "drying", "conditioning", "cold"]
    assert stages[0].nominal_end_at == datetime(2026, 9, 17, 8, 55)
    assert stages[0].maximum_end_at == datetime(2026, 9, 18, 14, 55)
    assert stages[1].entry_at == datetime(2026, 9, 17, 8, 55)
    assert stages[1].nominal_end_at == datetime(2026, 9, 18, 8, 55)
    assert stages[2].entry_at == datetime(2026, 9, 18, 8, 55)
    assert stages[2].nominal_end_at == datetime(2026, 9, 19, 8, 55)
    assert stages[2].maximum_end_at == datetime(2026, 9, 21, 8, 55)
    assert stages[3].entry_at == datetime(2026, 9, 19, 8, 55)
    assert stages[3].nominal_end_at == datetime(2026, 9, 20, 8, 55)
    assert stages[3].maximum_end_at == datetime(2026, 9, 20, 10, 55)

    warnings = _weekend_events(stages)
    assert any("sábado" in item for item in warnings)
    assert any("domingo" in item for item in warnings)


def test_conditioning_is_shown_even_when_cold_is_not_planned() -> None:
    stages = _project_climatic_stages(
        _details(drying_required=False),
        _workflow(cold_planned=False),
        datetime(2026, 8, 20, 8, 55),
    )

    assert [stage.key for stage in stages] == ["heat", "conditioning"]


def test_schedule_summary_names_cold_and_marks_weekend() -> None:
    stages = _project_climatic_stages(
        _details(),
        _workflow(),
        datetime(2026, 8, 20, 8, 55),
    )

    summary = _schedule_summary(stages)
    texts = _texts(summary)

    assert any("26.9 — Resistência térmica ao frio" in text for text in texts)
    assert "FIM DE SEMANA" in texts
    assert any("sábado" in text or "domingo" in text for text in texts)


def test_duplicate_cancel_card_is_removed_but_other_actions_remain() -> None:
    cancel = ft.Container(
        bgcolor=AppColors.DANGER_LIGHT,
        content=ft.Column(
            controls=[
                ft.Text("Cancelar este ensaio"),
                ft.Text("Escolha o motivo em uma janela de confirmação."),
                ft.Button(content="Cancelar ensaio"),
            ]
        ),
    )
    panel = ft.Column(
        controls=[
            ft.Text("Registrar agora"),
            ft.Divider(),
            cancel,
            ft.Divider(),
            ft.Text("Outra ação"),
        ]
    )

    _prune_duplicate_cancel(panel)
    texts = _texts(panel)

    assert "Cancelar este ensaio" not in texts
    assert "Registrar agora" in texts
    assert "Outra ação" in texts
