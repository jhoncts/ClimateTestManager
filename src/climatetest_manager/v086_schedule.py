"""Cronograma operacional completo antes do início dos ensaios climáticos.

A confirmação de entrada passa a mostrar a sequência nominal completa do ensaio:
calor, secagem quando aplicável, acondicionamento pós-calor e frio quando
planejado. Os marcos que caem em sábado ou domingo recebem destaque explícito.

As datas das etapas posteriores são projeções. Quando o operador registra o
horário real de uma transição, os prazos efetivos continuam sendo recalculados
pelos serviços existentes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import flet as ft

from climatetest_manager import production_app, v086_runtime
from climatetest_manager.services.climate_tests import ClimateTestDetails
from climatetest_manager.services.cold_workflows import ColdWorkflowSnapshot
from climatetest_manager.ui.components import dialog_actions, dialog_banner, styled_dialog
from climatetest_manager.ui.formatters import (
    format_decimal,
    format_operational_date,
)
from climatetest_manager.ui.theme import AppColors


@dataclass(frozen=True, slots=True)
class ProjectedStage:
    key: str
    title: str
    subtitle: str
    icon: ft.IconData
    accent: str
    accent_background: str
    condition: str
    entry_label: str
    nominal_label: str
    maximum_label: str
    entry_at: datetime
    nominal_end_at: datetime
    maximum_end_at: datetime
    projected_entry: bool = True


def _hours(value: int | None) -> int:
    return int(value or 0)


def _project_climatic_stages(
    details: ClimateTestDetails,
    workflow: ColdWorkflowSnapshot | None,
    entry_at: datetime,
) -> tuple[ProjectedStage, ...]:
    """Calcula a sequência nominal sem alterar nenhum registro do ensaio."""

    entry = entry_at.replace(microsecond=0)
    chamber_nominal = entry + timedelta(hours=details.chamber_duration_hours)
    chamber_maximum = chamber_nominal + timedelta(hours=details.chamber_duration_tolerance_hours)
    stages: list[ProjectedStage] = [
        ProjectedStage(
            key="heat",
            title="Câmara climática — calor",
            subtitle="Primeira etapa registrada ao confirmar esta entrada.",
            icon=ft.Icons.DEVICE_THERMOSTAT,
            accent=AppColors.PRIMARY,
            accent_background=AppColors.PRIMARY_LIGHT,
            condition=(
                f"{format_decimal(details.chamber_temperature_c)} °C • "
                f"{format_decimal(details.chamber_humidity_percent)} % UR • "
                f"{details.chamber_duration_hours} h"
            ),
            entry_label="ENTRADA",
            nominal_label="RETIRADA NOMINAL",
            maximum_label="LIMITE COM TOLERÂNCIA",
            entry_at=entry,
            nominal_end_at=chamber_nominal,
            maximum_end_at=chamber_maximum,
            projected_entry=False,
        )
    ]

    next_nominal_start = chamber_nominal
    if details.drying_required:
        drying_duration = _hours(details.drying_duration_hours)
        drying_tolerance = _hours(details.drying_duration_tolerance_hours)
        drying_nominal = next_nominal_start + timedelta(hours=drying_duration)
        drying_maximum = drying_nominal + timedelta(hours=drying_tolerance)
        drying_temperature = (
            f"{format_decimal(details.drying_temperature_c)} °C"
            if details.drying_temperature_c is not None
            else "Temperatura definida no ensaio"
        )
        stages.append(
            ProjectedStage(
                key="drying",
                title="Câmara seca — secagem",
                subtitle="Projeção considerando troca logo após a retirada nominal do calor.",
                icon=ft.Icons.DRY,
                accent=AppColors.WARNING,
                accent_background=AppColors.WARNING_LIGHT,
                condition=f"{drying_temperature} • {drying_duration} h",
                entry_label="ENTRADA PREVISTA",
                nominal_label="RETIRADA NOMINAL",
                maximum_label="LIMITE COM TOLERÂNCIA",
                entry_at=next_nominal_start,
                nominal_end_at=drying_nominal,
                maximum_end_at=drying_maximum,
            )
        )
        next_nominal_start = drying_nominal

    if workflow is not None:
        conditioning_start = next_nominal_start
        conditioning_nominal = conditioning_start + timedelta(hours=24)
        conditioning_maximum = conditioning_start + timedelta(hours=72)
        stages.append(
            ProjectedStage(
                key="conditioning",
                title="Acondicionamento pós-calor — 26.8",
                subtitle="Etapa obrigatória do novo fluxo após a conclusão do calor.",
                icon=ft.Icons.HOURGLASS_BOTTOM,
                accent=AppColors.INFO,
                accent_background=AppColors.INFO_LIGHT,
                condition="20 ± 5 °C • 50 ± 10 % UR • 24 a 72 h",
                entry_label="INÍCIO PREVISTO",
                nominal_label="MÍNIMO DE 24 H",
                maximum_label="LIMITE DE 72 H",
                entry_at=conditioning_start,
                nominal_end_at=conditioning_nominal,
                maximum_end_at=conditioning_maximum,
            )
        )

        if workflow.cold_planned:
            cold_start = conditioning_nominal
            cold_nominal = cold_start + timedelta(hours=24)
            cold_maximum = cold_start + timedelta(hours=26)
            stages.append(
                ProjectedStage(
                    key="cold",
                    title="26.9 — Resistência térmica ao frio",
                    subtitle=(
                        "Primeira previsão possível após completar o mínimo de 24 h "
                        "de acondicionamento."
                    ),
                    icon=ft.Icons.AC_UNIT,
                    accent=AppColors.INFO,
                    accent_background=AppColors.INFO_LIGHT,
                    condition=(
                        f"{format_decimal(workflow.temperature_range.minimum_c)} °C a "
                        f"{format_decimal(workflow.temperature_range.maximum_c)} °C • "
                        "24 a 26 h"
                    ),
                    entry_label="ENTRADA PREVISTA",
                    nominal_label="RETIRADA EM 24 H",
                    maximum_label="LIMITE DE 26 H",
                    entry_at=cold_start,
                    nominal_end_at=cold_nominal,
                    maximum_end_at=cold_maximum,
                )
            )

    return tuple(stages)


def _weekend_events(stages: tuple[ProjectedStage, ...]) -> tuple[str, ...]:
    """Lista cada marco projetado que exige atenção no fim de semana."""

    events: list[str] = []
    for stage in stages:
        for label, value in (
            (stage.entry_label, stage.entry_at),
            (stage.nominal_label, stage.nominal_end_at),
            (stage.maximum_label, stage.maximum_end_at),
        ):
            if value.weekday() < 5:
                continue
            weekday, date_text, time_text = format_operational_date(value)
            events.append(
                f"{stage.title}: {label.lower()} em {weekday}, {date_text} às {time_text}"
            )
    return tuple(events)


def _moment_card(label: str, value: datetime, *, projected: bool) -> ft.Container:
    weekday, date_text, time_text = format_operational_date(value)
    weekend = value.weekday() >= 5
    label_text = f"{label} • PREVISÃO" if projected else label
    return ft.Container(
        col={"xs": 12, "sm": 4},
        border_radius=11,
        bgcolor=AppColors.DANGER_LIGHT if weekend else AppColors.SURFACE,
        border=ft.Border.all(1, AppColors.DANGER if weekend else AppColors.DIVIDER),
        padding=10,
        content=ft.Column(
            spacing=3,
            controls=[
                ft.Row(
                    spacing=6,
                    controls=[
                        ft.Text(
                            label_text,
                            expand=True,
                            size=9.5,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.DANGER if weekend else AppColors.TEXT_SECONDARY,
                        ),
                        *(
                            [
                                ft.Container(
                                    border_radius=8,
                                    bgcolor=AppColors.DANGER,
                                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                    content=ft.Text(
                                        "FIM DE SEMANA",
                                        size=8,
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.WHITE,
                                    ),
                                )
                            ]
                            if weekend
                            else []
                        ),
                    ],
                ),
                ft.Text(
                    weekday,
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                ft.Text(
                    f"{date_text} às {time_text}",
                    size=13,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
            ],
        ),
    )


def _stage_card(stage: ProjectedStage, index: int) -> ft.Container:
    return ft.Container(
        border_radius=14,
        bgcolor=AppColors.PAGE_BACKGROUND,
        border=ft.Border.all(1, AppColors.DIVIDER),
        padding=13,
        content=ft.Column(
            spacing=9,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=38,
                            height=38,
                            border_radius=11,
                            bgcolor=stage.accent_background,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(stage.icon, size=20, color=stage.accent),
                        ),
                        ft.Column(
                            expand=True,
                            spacing=1,
                            controls=[
                                ft.Text(
                                    f"{index}. {stage.title}",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    stage.subtitle,
                                    size=10,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                        ft.Container(
                            border_radius=10,
                            bgcolor=stage.accent_background,
                            padding=ft.Padding.symmetric(horizontal=9, vertical=5),
                            content=ft.Text(
                                stage.condition,
                                size=10,
                                weight=ft.FontWeight.W_500,
                                color=stage.accent,
                            ),
                        ),
                    ],
                ),
                ft.ResponsiveRow(
                    spacing=8,
                    run_spacing=8,
                    controls=[
                        _moment_card(
                            stage.entry_label,
                            stage.entry_at,
                            projected=stage.projected_entry,
                        ),
                        _moment_card(
                            stage.nominal_label,
                            stage.nominal_end_at,
                            projected=True,
                        ),
                        _moment_card(
                            stage.maximum_label,
                            stage.maximum_end_at,
                            projected=True,
                        ),
                    ],
                ),
            ],
        ),
    )


def _schedule_summary(stages: tuple[ProjectedStage, ...]) -> ft.Column:
    weekend = _weekend_events(stages)
    controls: list[ft.Control] = [
        dialog_banner(
            "As etapas seguintes usam a sequência nominal como previsão. "
            "Quando uma entrada ou retirada real for registrada, o sistema recalcula "
            "os prazos efetivos a partir daquele horário."
        )
    ]
    controls.extend(_stage_card(stage, index) for index, stage in enumerate(stages, start=1))
    if weekend:
        details = "\n".join(f"• {item}" for item in weekend)
        controls.append(
            dialog_banner(
                "Atenção: há marcos previstos para sábado ou domingo.\n" + details,
                icon=ft.Icons.WARNING_AMBER,
                warning=True,
            )
        )
    else:
        controls.append(
            dialog_banner(
                "Nenhum dos marcos previstos deste cronograma cai em sábado ou domingo.",
                icon=ft.Icons.EVENT_AVAILABLE,
            )
        )
    return ft.Column(
        width=900,
        tight=True,
        spacing=11,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=controls,
    )


def _contains_exact_text(control: ft.Control, value: str) -> bool:
    if isinstance(control, ft.Text) and str(control.value or "") == value:
        return True
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control) and _contains_exact_text(content, value):
        return True
    for child in getattr(control, "controls", ()) or ():
        if isinstance(child, ft.Control) and _contains_exact_text(child, value):
            return True
    return False


def _is_duplicate_cancel_block(control: ft.Control) -> bool:
    return (
        isinstance(control, ft.Container)
        and control.bgcolor == AppColors.DANGER_LIGHT
        and _contains_exact_text(control, "Cancelar este ensaio")
    )


def _prune_duplicate_cancel(control: ft.Control) -> ft.Control:
    """Remove só o card de cancelamento duplicado; o menu Ações é preservado."""

    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        _prune_duplicate_cancel(content)

    children = getattr(control, "controls", None)
    if not isinstance(children, list):
        return control

    kept: list[ft.Control] = []
    for child in children:
        if not isinstance(child, ft.Control):
            continue
        if _is_duplicate_cancel_block(child):
            if kept and isinstance(kept[-1], ft.Divider):
                kept.pop()
            continue
        _prune_duplicate_cancel(child)
        if isinstance(child, ft.Divider) and kept and isinstance(kept[-1], ft.Divider):
            continue
        kept.append(child)
    while kept and isinstance(kept[-1], ft.Divider):
        kept.pop()
    children[:] = kept
    return control


def _confirm_climatic_start(
    self: v086_runtime.V086DetailsView,
    started_at: datetime | None,
) -> None:
    effective_start = (started_at or datetime.now()).replace(microsecond=0)
    stages = _project_climatic_stages(self._details, self._v086_cold, effective_start)
    page = self.root.page

    def confirm(_event: object | None = None) -> None:
        page.pop_dialog()
        self._on_start_chamber(effective_start)

    page.show_dialog(
        styled_dialog(
            title="Confirmar início dos ensaios climáticos?",
            subtitle="Confira as etapas, os limites e os dias da semana antes de registrar",
            icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
            scrollable=True,
            content=_schedule_summary(stages),
            actions=dialog_actions(
                page=page,
                primary_label="Confirmar entrada",
                primary_icon=ft.Icons.CHECK,
                on_confirm=confirm,
                cancel_label="Voltar e revisar",
            ),
        )
    )


def install() -> None:
    if getattr(production_app, "_v086_schedule_installed", False):
        return

    current_action_panel = v086_runtime.V086DetailsView._action_panel

    def action_panel_without_duplicate(self: v086_runtime.V086DetailsView):
        return _prune_duplicate_cancel(current_action_panel(self))

    v086_runtime.V086DetailsView._action_panel = action_panel_without_duplicate
    v086_runtime.V086DetailsView._confirm_chamber_start = _confirm_climatic_start
    production_app._v086_schedule_installed = True
