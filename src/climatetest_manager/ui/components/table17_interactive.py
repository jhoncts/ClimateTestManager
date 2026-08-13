"""Tabela 17 interativa usada pela experiência R7.

A tabela continua sendo somente uma representação visual das regras já implementadas
em ``domain.climate_rules``. O motor normativo permanece como fonte de verdade.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

import flet as ft

from climatetest_manager.domain.climate_rules import available_options
from climatetest_manager.domain.enums import TestOption
from climatetest_manager.ui.components.table17 import _ROWS, _RuleRow
from climatetest_manager.ui.theme import AppColors

GROUP_EPLS: dict[str, tuple[str, ...]] = {
    "G1": ("Ga", "Gb", "Da", "Db", "Ma", "Mb"),
    "G2": ("Gc", "Dc"),
}


def _row_matches_ts(row: _RuleRow, ts: Decimal) -> bool:
    if row.group == "G1":
        if row.rule_a.startswith("G1-LOW"):
            return ts <= Decimal("70")
        if row.rule_a.startswith("G1-MID"):
            return Decimal("70") < ts < Decimal("75")
        return ts >= Decimal("75")
    if row.rule_a.startswith("G2-LOW"):
        return ts <= Decimal("80")
    if row.rule_a.startswith("G2-MID"):
        return Decimal("80") < ts <= Decimal("85")
    return ts > Decimal("85")


def matching_row(epl: str | None, ts: Decimal | None) -> _RuleRow | None:
    if not epl or ts is None:
        return None
    group = "G2" if epl in GROUP_EPLS["G2"] else "G1"
    return next((row for row in _ROWS if row.group == group and _row_matches_ts(row, ts)), None)


def ts_band_label(epl: str | None, ts: Decimal | None) -> str:
    row = matching_row(epl, ts)
    return row.ts_band if row is not None else "Aguardando seleção"


def _epl_selector(
    group: str,
    *,
    selected_epl: str | None,
    enabled: bool,
    on_select_epl: Callable[[str], None],
) -> ft.Container:
    chips: list[ft.Control] = []
    for epl in GROUP_EPLS[group]:
        selected = epl == selected_epl
        chip = ft.Container(
            width=44,
            height=30,
            alignment=ft.Alignment.CENTER,
            border_radius=8,
            bgcolor=AppColors.PRIMARY_LIGHT if selected else AppColors.SURFACE,
            border=ft.Border.all(
                2 if selected else 1,
                AppColors.PRIMARY if selected else AppColors.DIVIDER,
            ),
            opacity=1 if enabled else 0.42,
            tooltip=(
                f"EPL {epl} selecionado"
                if selected
                else f"Selecionar EPL {epl}"
                if enabled
                else "Informe o Ts antes de selecionar o EPL"
            ),
            on_click=(lambda _event, value=epl: on_select_epl(value)) if enabled else None,
            content=ft.Text(
                epl,
                size=10,
                weight=ft.FontWeight.BOLD if selected else ft.FontWeight.W_500,
                color=AppColors.PRIMARY if selected else AppColors.TEXT_PRIMARY,
            ),
        )
        chips.append(chip)
    return ft.Container(
        width=116,
        padding=8,
        bgcolor=AppColors.PAGE_BACKGROUND,
        border=ft.Border.all(1, AppColors.DIVIDER),
        content=ft.Column(
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=chips,
        ),
    )


def _text_cell(
    text: str,
    *,
    width: int | None = None,
    header: bool = False,
    disabled: bool = False,
    selected: bool = False,
    on_click: Callable[[], None] | None = None,
    tooltip: str | None = None,
) -> ft.Container:
    interactive = on_click is not None and not disabled
    return ft.Container(
        width=width,
        min_height=48 if header else 72,
        padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        bgcolor=(
            AppColors.PRIMARY_LIGHT
            if selected
            else AppColors.PAGE_BACKGROUND
            if header
            else AppColors.SURFACE
        ),
        border=ft.Border.all(
            2 if selected else 1,
            AppColors.PRIMARY if selected else AppColors.DIVIDER,
        ),
        opacity=0.38 if disabled else 1,
        alignment=ft.Alignment.CENTER_LEFT,
        tooltip=tooltip,
        on_click=(lambda _event: on_click()) if interactive else None,
        animate=ft.Animation(140, ft.AnimationCurve.EASE_OUT_CUBIC),
        content=ft.Text(
            text,
            size=10 if not header else 11,
            weight=ft.FontWeight.BOLD if header or selected else ft.FontWeight.NORMAL,
            color=AppColors.PRIMARY if selected else AppColors.TEXT_PRIMARY,
            text_align=ft.TextAlign.CENTER if header else ft.TextAlign.LEFT,
        ),
    )


def build_interactive_table17(
    *,
    ts: Decimal | None,
    selected_epl: str | None,
    selected_option: str | None,
    on_select_epl: Callable[[str], None],
    on_select_option: Callable[[str], None],
) -> ft.Control:
    """Monta a Tabela 17 em largura fixa e permite exatamente 1 EPL e 1 condição."""

    table_width = 980
    selected_group = (
        "G2" if selected_epl in GROUP_EPLS["G2"] else "G1" if selected_epl else None
    )
    selected_row = matching_row(selected_epl, ts)
    valid_options: set[str] = set()
    if selected_epl and ts is not None:
        try:
            valid_options = {option.value for option in available_options(selected_epl, ts)}
        except (ValueError, TypeError):
            valid_options = set()

    rows: list[ft.Control] = []
    first_group_row: dict[str, bool] = {"G1": True, "G2": True}
    for row in _ROWS:
        row_matches = ts is not None and _row_matches_ts(row, ts)
        group_selected = selected_group == row.group
        selection_row = selected_row is row
        epl_cell: ft.Control
        if first_group_row[row.group]:
            epl_cell = _epl_selector(
                row.group,
                selected_epl=selected_epl,
                enabled=ts is not None,
                on_select_epl=on_select_epl,
            )
            first_group_row[row.group] = False
        else:
            epl_cell = ft.Container(
                width=116,
                bgcolor=AppColors.PAGE_BACKGROUND,
                border=ft.Border.all(1, AppColors.DIVIDER),
            )

        option_a_enabled = bool(
            group_selected and row_matches and TestOption.A.value in valid_options
        )
        option_b_enabled = bool(
            group_selected
            and row_matches
            and row.rule_b
            and TestOption.B.value in valid_options
        )
        rows.append(
            ft.Row(
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    epl_cell,
                    _text_cell(
                        row.ts_band,
                        width=170,
                        disabled=bool(ts is not None and not row_matches),
                        selected=bool(selection_row),
                    ),
                    ft.Container(
                        width=347,
                        content=_text_cell(
                            row.option_a,
                            disabled=not option_a_enabled,
                            selected=bool(selection_row and selected_option == "A"),
                            on_click=(
                                (lambda: on_select_option("A")) if option_a_enabled else None
                            ),
                            tooltip=(
                                "Selecionar esta condição"
                                if option_a_enabled
                                else "Esta condição não corresponde ao EPL e Ts selecionados"
                            ),
                        ),
                    ),
                    ft.Container(
                        width=347,
                        content=_text_cell(
                            row.option_b,
                            disabled=not option_b_enabled,
                            selected=bool(selection_row and selected_option == "B"),
                            on_click=(
                                (lambda: on_select_option("B")) if option_b_enabled else None
                            ),
                            tooltip=(
                                "Selecionar esta condição"
                                if option_b_enabled
                                else "Esta alternativa não é permitida para o EPL e Ts selecionados"
                            ),
                        ),
                    ),
                ],
            )
        )

    table = ft.Container(
        width=table_width,
        border_radius=12,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        border=ft.Border.all(1, AppColors.DIVIDER),
        content=ft.Column(
            spacing=0,
            controls=[
                ft.Row(
                    spacing=0,
                    controls=[
                        _text_cell("EPL", width=116, header=True),
                        _text_cell("Temperatura de serviço Ts", width=170, header=True),
                        ft.Container(
                            width=347,
                            content=_text_cell("Condição do ensaio • A", header=True),
                        ),
                        ft.Container(
                            width=347,
                            content=_text_cell("Condição do ensaio • B", header=True),
                        ),
                    ],
                ),
                *rows,
            ],
        ),
    )
    return ft.Column(
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            ft.Row(
                wrap=True,
                run_spacing=6,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(
                        "Clique primeiro no EPL e depois na condição desejada.",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        (
                            "Informe o Ts para liberar as opções."
                            if ts is None
                            else "Opções incompatíveis com o Ts informado ficam desabilitadas."
                        ),
                        size=10,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                ],
            ),
            ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
                controls=[table],
            ),
        ],
    )
