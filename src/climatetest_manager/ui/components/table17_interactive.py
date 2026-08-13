"""Tabela 17 interativa com uma árvore visual persistente.

O motor normativo em :mod:`climatetest_manager.domain.climate_rules` continua
sendo a única fonte de verdade. Este componente nunca substitui controles após
ser montado: ``set_state`` altera somente propriedades visuais. Isso evita a
perda de conteúdo observada no WebView2 durante digitação e rolagem.
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


def _cell(
    text: str,
    *,
    width: int,
    header: bool = False,
    alignment: ft.Alignment = ft.Alignment.CENTER_LEFT,
) -> ft.Container:
    return ft.Container(
        width=width,
        height=46 if header else 66,
        padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        bgcolor=AppColors.PAGE_BACKGROUND if header else AppColors.SURFACE,
        border=ft.Border.all(1, AppColors.DIVIDER),
        alignment=alignment,
        content=ft.Text(
            text,
            size=10 if not header else 11,
            weight=ft.FontWeight.BOLD if header else ft.FontWeight.NORMAL,
            color=AppColors.TEXT_PRIMARY,
            text_align=ft.TextAlign.CENTER if header else ft.TextAlign.LEFT,
        ),
    )


class InteractiveTable17(ft.Column):
    """Tabela estável que permite selecionar exatamente um EPL e uma condição."""

    TABLE_WIDTH = 980

    def __init__(
        self,
        *,
        ts: Decimal | None,
        selected_epl: str | None,
        selected_option: str | None,
        on_select_epl: Callable[[str], None],
        on_select_option: Callable[[str], None],
        on_invalid: Callable[[str], None] | None = None,
    ) -> None:
        self._on_select_epl = on_select_epl
        self._on_select_option = on_select_option
        self._on_invalid = on_invalid
        self._epl_chips: dict[str, ft.Container] = {}
        self._band_cells: list[tuple[_RuleRow, ft.Container]] = []
        self._option_cells: list[tuple[_RuleRow, str, ft.Container]] = []
        self._instruction = ft.Text(size=10, color=AppColors.TEXT_SECONDARY)
        self._selection = ft.Text(
            size=10,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )

        table = self._build_table()
        super().__init__(
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(
                    wrap=True,
                    run_spacing=6,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(
                            "Selecione o EPL e depois uma condição aplicável.",
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                        self._instruction,
                    ],
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[table],
                ),
                ft.Container(
                    border_radius=10,
                    bgcolor=AppColors.INFO_LIGHT,
                    border=ft.Border.all(1, AppColors.DIVIDER),
                    padding=ft.Padding.symmetric(horizontal=11, vertical=8),
                    content=ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(
                                ft.Icons.VERIFIED_USER_OUTLINED,
                                size=16,
                                color=AppColors.PRIMARY,
                            ),
                            self._selection,
                        ],
                    ),
                ),
            ],
        )
        self.set_state(ts=ts, selected_epl=selected_epl, selected_option=selected_option)

    def _build_epl_chip(self, epl: str) -> ft.Container:
        label = ft.Text(
            epl,
            size=10,
            weight=ft.FontWeight.W_500,
            color=AppColors.TEXT_PRIMARY,
        )
        chip = ft.Container(
            width=50,
            height=32,
            alignment=ft.Alignment.CENTER,
            border_radius=8,
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            animate=ft.Animation(120, ft.AnimationCurve.EASE_OUT_CUBIC),
            content=label,
        )
        self._epl_chips[epl] = chip
        return chip

    def _build_option_cell(self, row: _RuleRow, option: str) -> ft.Container:
        text = row.option_a if option == TestOption.A.value else row.option_b
        cell = _cell(text, width=347)
        cell.animate = ft.Animation(120, ft.AnimationCurve.EASE_OUT_CUBIC)
        self._option_cells.append((row, option, cell))
        return cell

    def _build_table(self) -> ft.Container:
        selector = ft.Container(
            width=864,
            height=50,
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            content=ft.Row(
                spacing=7,
                controls=[
                    *[self._build_epl_chip(epl) for epl in GROUP_EPLS["G1"]],
                    ft.Container(width=1, height=24, bgcolor=AppColors.DIVIDER),
                    *[self._build_epl_chip(epl) for epl in GROUP_EPLS["G2"]],
                ],
            ),
        )
        rows: list[ft.Control] = []
        for row in _ROWS:
            band = _cell(row.ts_band, width=170)
            band.animate = ft.Animation(120, ft.AnimationCurve.EASE_OUT_CUBIC)
            self._band_cells.append((row, band))
            rows.append(
                ft.Row(
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        _cell(
                            "Ga–Mb" if row.group == "G1" else "Gc / Dc",
                            width=116,
                            alignment=ft.Alignment.CENTER,
                        ),
                        band,
                        self._build_option_cell(row, TestOption.A.value),
                        self._build_option_cell(row, TestOption.B.value),
                    ],
                )
            )

        return ft.Container(
            width=self.TABLE_WIDTH,
            border_radius=12,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            border=ft.Border.all(1, AppColors.DIVIDER),
            content=ft.Column(
                spacing=0,
                controls=[
                    ft.Row(
                        spacing=0,
                        controls=[
                            _cell("Grupo EPL", width=116, header=True),
                            _cell("Temperatura de serviço Ts", width=170, header=True),
                            _cell("Condição do ensaio • A", width=347, header=True),
                            _cell("Condição do ensaio • B", width=347, header=True),
                        ],
                    ),
                    ft.Row(
                        spacing=0,
                        controls=[
                            _cell(
                                "EPL",
                                width=116,
                                header=True,
                                alignment=ft.Alignment.CENTER,
                            ),
                            selector,
                        ],
                    ),
                    *rows,
                ],
            ),
        )

    def _invalid(self, message: str) -> None:
        if self._on_invalid is not None:
            self._on_invalid(message)

    def set_state(
        self,
        *,
        ts: Decimal | None,
        selected_epl: str | None,
        selected_option: str | None,
    ) -> None:
        """Atualiza o realce sem substituir nenhum filho já montado."""

        selected_group = (
            "G2" if selected_epl in GROUP_EPLS["G2"] else "G1" if selected_epl else None
        )
        selected_row = matching_row(selected_epl, ts)
        valid_options: set[str] = set()
        if selected_epl and ts is not None:
            try:
                valid_options = {option.value for option in available_options(selected_epl, ts)}
            except (TypeError, ValueError):
                valid_options = set()

        for epl, chip in self._epl_chips.items():
            selected = epl == selected_epl
            label = chip.content
            chip.bgcolor = AppColors.PRIMARY_LIGHT if selected else AppColors.SURFACE
            chip.border = ft.Border.all(
                2 if selected else 1,
                AppColors.PRIMARY if selected else AppColors.DIVIDER,
            )
            chip.opacity = 1 if ts is not None else 0.5
            chip.tooltip = (
                f"EPL {epl} selecionado"
                if selected
                else f"Selecionar EPL {epl}"
                if ts is not None
                else "Informe o Ts antes de selecionar o EPL"
            )
            chip.on_click = (
                (lambda _event, value=epl: self._on_select_epl(value))
                if ts is not None
                else lambda _event: self._invalid("Informe o Ts antes de selecionar o EPL.")
            )
            if isinstance(label, ft.Text):
                label.weight = ft.FontWeight.BOLD if selected else ft.FontWeight.W_500
                label.color = AppColors.PRIMARY if selected else AppColors.TEXT_PRIMARY

        for row, cell in self._band_cells:
            row_matches = ts is not None and _row_matches_ts(row, ts)
            active = selected_row is row
            cell.bgcolor = AppColors.PRIMARY_LIGHT if active else AppColors.SURFACE
            cell.border = ft.Border.all(
                2 if active else 1,
                AppColors.PRIMARY if active else AppColors.DIVIDER,
            )
            cell.opacity = 1 if ts is None or row_matches else 0.35

        for row, option, cell in self._option_cells:
            row_matches = ts is not None and _row_matches_ts(row, ts)
            same_group = selected_group == row.group
            has_option = option == TestOption.A.value or row.rule_b is not None
            enabled = bool(same_group and row_matches and has_option and option in valid_options)
            active = bool(enabled and selected_row is row and selected_option == option)
            cell.bgcolor = AppColors.PRIMARY_LIGHT if active else AppColors.SURFACE
            cell.border = ft.Border.all(
                2 if active else 1,
                AppColors.PRIMARY if active else AppColors.DIVIDER,
            )
            cell.opacity = 1 if enabled else 0.32
            if active:
                reason = f"Condição {option} selecionada"
            elif enabled:
                reason = "Selecionar esta condição"
            elif ts is None:
                reason = "Informe o Ts para verificar esta condição"
            elif not selected_epl:
                reason = "Selecione um EPL para verificar esta condição"
            elif not same_group or not row_matches:
                reason = "Esta linha não corresponde ao EPL e ao Ts informados"
            elif not has_option:
                reason = "Esta faixa não possui alternativa B"
            else:
                reason = "Esta alternativa não é permitida para o EPL e o Ts informados"
            cell.tooltip = reason
            cell.on_click = (
                (lambda _event, value=option: self._on_select_option(value))
                if enabled
                else lambda _event, message=reason: self._invalid(message + ".")
            )
            label = cell.content
            if isinstance(label, ft.Text):
                label.weight = ft.FontWeight.BOLD if active else ft.FontWeight.NORMAL
                label.color = AppColors.PRIMARY if active else AppColors.TEXT_PRIMARY

        self._instruction.value = (
            "Informe o Ts para liberar a seleção."
            if ts is None
            else "Selecione um EPL."
            if not selected_epl
            else "Selecione uma das condições realçadas."
            if not selected_option
            else "Seleção válida e pronta para salvar."
        )
        ts_label = str(ts).replace(".", ",") if ts is not None else "—"
        self._selection.value = (
            f"Ts = {ts_label} °C • EPL {selected_epl or '—'} • Condição {selected_option or '—'}"
        )


def build_interactive_table17(
    *,
    ts: Decimal | None,
    selected_epl: str | None,
    selected_option: str | None,
    on_select_epl: Callable[[str], None],
    on_select_option: Callable[[str], None],
    on_invalid: Callable[[str], None] | None = None,
) -> InteractiveTable17:
    """Cria a tabela persistente mantendo a API usada pelas telas anteriores."""

    return InteractiveTable17(
        ts=ts,
        selected_epl=selected_epl,
        selected_option=selected_option,
        on_select_epl=on_select_epl,
        on_select_option=on_select_option,
        on_invalid=on_invalid,
    )
