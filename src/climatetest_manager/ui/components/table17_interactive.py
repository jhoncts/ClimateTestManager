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
from climatetest_manager.domain.enums import EPL, TestOption
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
        height=42 if header else 58,
        padding=ft.Padding.symmetric(horizontal=9, vertical=6),
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

    TABLE_WIDTH = 1016
    TABLE_BODY_HEIGHT = 42 + (len(EPL) * 58)
    CONTROL_HEIGHT = 570

    def __init__(
        self,
        *,
        ts: Decimal | None,
        selected_epl: str | None,
        selected_option: str | None,
        on_select_epl: Callable[[str], None],
        on_select_option: Callable[[str], None],
        on_invalid: Callable[[str], None] | None = None,
        interactive: bool = True,
    ) -> None:
        self._on_select_epl = on_select_epl
        self._on_select_option = on_select_option
        self._on_invalid = on_invalid
        self._interactive = bool(interactive)
        # ContextVar não atravessa necessariamente callbacks tardios do WebView2.
        # Guardamos o tema da sessão que construiu a tabela e o reativamos antes
        # de qualquer atualização/click para o realce nunca voltar ao teal padrão.
        self._theme_mode = AppColors.current_mode()
        self._epl_chips: dict[str, ft.Container] = {}
        self._band_cells: list[tuple[str, ft.Container]] = []
        self._option_cells: list[tuple[str, str, ft.Container]] = []
        self._data_rows: list[ft.Row] = []
        self._lead_instruction = ft.Text(
            "Selecione o EPL e depois uma condição aplicável.",
            size=11,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )
        self._instruction = ft.Text(size=10, color=AppColors.TEXT_SECONDARY)
        self._selection = ft.Text(
            size=10,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )

        table = self._build_table()
        super().__init__(
            height=self.CONTROL_HEIGHT,
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(
                    wrap=True,
                    run_spacing=6,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        self._lead_instruction,
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
        self.set_state(
            ts=ts,
            selected_epl=selected_epl,
            selected_option=selected_option,
            interactive=interactive,
        )

    def _build_epl_chip(self, epl: str) -> ft.Container:
        label = ft.Text(
            epl,
            size=10,
            weight=ft.FontWeight.W_500,
            color=AppColors.TEXT_PRIMARY,
        )
        chip = ft.Container(
            width=86,
            height=58,
            alignment=ft.Alignment.CENTER,
            border_radius=0,
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            animate=ft.Animation(120, ft.AnimationCurve.EASE_OUT_CUBIC),
            content=label,
        )
        self._epl_chips[epl] = chip
        return chip

    def _build_option_cell(self, epl: str, option: str) -> ft.Container:
        cell = _cell("Informe o Ts", width=375)
        cell.animate = ft.Animation(120, ft.AnimationCurve.EASE_OUT_CUBIC)
        self._option_cells.append((epl, option, cell))
        return cell

    def _build_table(self) -> ft.Container:
        rows: list[ft.Control] = []
        for epl_item in EPL:
            epl = epl_item.value
            band = _cell("Aguardando Ts", width=180)
            band.animate = ft.Animation(120, ft.AnimationCurve.EASE_OUT_CUBIC)
            self._band_cells.append((epl, band))
            data_row = ft.Row(
                height=58,
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self._build_epl_chip(epl),
                    band,
                    self._build_option_cell(epl, TestOption.A.value),
                    self._build_option_cell(epl, TestOption.B.value),
                ],
            )
            self._data_rows.append(data_row)
            rows.append(data_row)

        return ft.Container(
            width=self.TABLE_WIDTH,
            height=self.TABLE_BODY_HEIGHT,
            border_radius=12,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            border=ft.Border.all(1, AppColors.DIVIDER),
            content=ft.Column(
                spacing=0,
                controls=[
                    ft.Row(
                        height=42,
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            _cell(
                                "EPL",
                                width=86,
                                header=True,
                                alignment=ft.Alignment.CENTER,
                            ),
                            _cell("Temperatura de serviço Ts", width=180, header=True),
                            _cell("Condição do ensaio • A", width=375, header=True),
                            _cell("Condição do ensaio • B", width=375, header=True),
                        ],
                    ),
                    *rows,
                ],
            ),
        )

    def _activate_theme(self) -> None:
        """Restaura a paleta desta sessão antes de callbacks tardios."""

        mode = self._theme_mode
        try:
            page_mode = getattr(self.page, "_climatetest_theme_mode", None)
        except (AttributeError, RuntimeError):
            page_mode = None
        if page_mode:
            mode = AppColors.normalize_mode(str(page_mode))
            self._theme_mode = mode
        AppColors.apply_mode(mode)

    def _invalid(self, message: str) -> None:
        self._activate_theme()
        if self._on_invalid is not None:
            self._on_invalid(message)

    def set_state(
        self,
        *,
        ts: Decimal | None,
        selected_epl: str | None,
        selected_option: str | None,
        interactive: bool | None = None,
    ) -> None:
        """Atualiza o realce sem substituir nenhum filho já montado.

        Quando ``interactive`` é falso a tabela continua mostrando EPL, faixa e
        condição calculados, porém funciona somente como conferência visual.
        Isso impede que uma visualização avançada altere um ensaio configurado
        por Tamb + ΔT ou por Ts informado.
        """

        self._activate_theme()
        if interactive is not None:
            self._interactive = bool(interactive)
        for epl, chip in self._epl_chips.items():
            selected = epl == selected_epl
            label = chip.content
            chip.bgcolor = AppColors.PRIMARY_LIGHT if selected else AppColors.SURFACE
            chip.border = ft.Border.all(
                2 if selected else 1,
                AppColors.PRIMARY if selected else AppColors.DIVIDER,
            )
            chip.opacity = 1 if selected else 0.82 if ts is not None else 0.45
            if not self._interactive:
                chip.tooltip = (
                    f"EPL {epl} selecionado • somente visualização"
                    if selected
                    else "Somente visualização. Use 'Selecionar na Tabela 17' para editar."
                )
                chip.on_click = None
            else:
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

        for epl, cell in self._band_cells:
            active = epl == selected_epl
            row = matching_row(epl, ts)
            label = cell.content
            if isinstance(label, ft.Text):
                label.value = row.ts_band if row is not None else "Aguardando Ts"
                label.weight = ft.FontWeight.BOLD if active else ft.FontWeight.NORMAL
                label.color = AppColors.PRIMARY if active else AppColors.TEXT_PRIMARY
            cell.bgcolor = AppColors.PRIMARY_LIGHT if active else AppColors.SURFACE
            cell.border = ft.Border.all(
                2 if active else 1,
                AppColors.PRIMARY if active else AppColors.DIVIDER,
            )
            cell.opacity = 1 if active else 0.72 if ts is not None else 0.4

        for epl, option, cell in self._option_cells:
            row = matching_row(epl, ts)
            valid_options: set[str] = set()
            if ts is not None:
                try:
                    valid_options = {item.value for item in available_options(epl, ts)}
                except (TypeError, ValueError):
                    valid_options = set()
            text = (
                row.option_a
                if row is not None and option == TestOption.A.value
                else row.option_b
                if row is not None
                else "Informe o Ts"
            )
            has_option = bool(text and text != "—")
            enabled = bool(ts is not None and has_option and option in valid_options)
            active = bool(enabled and selected_epl == epl and selected_option == option)
            cell.bgcolor = AppColors.PRIMARY_LIGHT if active else AppColors.SURFACE
            cell.border = ft.Border.all(
                2 if active else 1,
                AppColors.PRIMARY if active else AppColors.DIVIDER,
            )
            cell.opacity = 1 if active else 0.72 if enabled else 0.28
            if active:
                reason = f"Condição {option} selecionada"
            elif enabled:
                reason = f"Selecionar EPL {epl} e condição {option}"
            elif ts is None:
                reason = "Informe o Ts para verificar esta condição"
            elif not has_option:
                reason = "Esta faixa não possui alternativa B"
            else:
                reason = "Esta alternativa não é permitida para o EPL e o Ts informados"
            if not self._interactive:
                cell.tooltip = (
                    f"Condição {option} aplicada • somente visualização"
                    if active
                    else "Somente visualização. Use 'Selecionar na Tabela 17' para editar."
                )
                cell.on_click = None
            else:
                cell.tooltip = reason
                cell.on_click = (
                    (
                        lambda _event, epl_value=epl, option_value=option: self._select_condition(
                            epl_value,
                            option_value,
                        )
                    )
                    if enabled
                    else lambda _event, message=reason: self._invalid(message + ".")
                )
            label = cell.content
            if isinstance(label, ft.Text):
                label.value = text
                label.weight = ft.FontWeight.BOLD if active else ft.FontWeight.NORMAL
                label.color = AppColors.PRIMARY if active else AppColors.TEXT_PRIMARY

        if not self._interactive:
            self._lead_instruction.value = "Tabela 17 — conferência da condição aplicada"
            self._instruction.value = (
                "Somente visualização • para editar, escolha 'Selecionar na Tabela 17'."
            )
        else:
            self._lead_instruction.value = "Selecione o EPL e depois uma condição aplicável."
            if ts is None:
                self._instruction.value = "Informe o Ts para liberar a seleção."
            elif not selected_epl or not selected_option:
                self._instruction.value = (
                    "Selecione diretamente uma condição na linha do EPL desejado."
                )
            else:
                self._instruction.value = "Seleção válida e pronta para salvar."
        ts_label = str(ts).replace(".", ",") if ts is not None else "—"
        self._selection.value = (
            f"Ts = {ts_label} °C • EPL {selected_epl or '—'} • Condição {selected_option or '—'}"
        )

    def _select_condition(self, epl: str, option: str) -> None:
        """Aplica EPL e alternativa com um único clique quando a tabela é editável."""

        self._activate_theme()
        if not self._interactive:
            self._invalid(
                "A Tabela 17 está somente para visualização. "
                "Escolha 'Selecionar na Tabela 17' para alterar a condição."
            )
            return
        self._on_select_epl(epl)
        self._on_select_option(option)


def build_interactive_table17(
    *,
    ts: Decimal | None,
    selected_epl: str | None,
    selected_option: str | None,
    on_select_epl: Callable[[str], None],
    on_select_option: Callable[[str], None],
    on_invalid: Callable[[str], None] | None = None,
    interactive: bool = True,
) -> InteractiveTable17:
    """Cria a tabela persistente mantendo a API usada pelas telas anteriores."""

    return InteractiveTable17(
        ts=ts,
        selected_epl=selected_epl,
        selected_option=selected_option,
        on_select_epl=on_select_epl,
        on_select_option=on_select_option,
        on_invalid=on_invalid,
        interactive=interactive,
    )
