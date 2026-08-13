"""Rodada 7: experiência clean, Tabela 17 interativa e ações seguras.

A R7 parte da base R6 validada no Windows e mantém a regra mais importante das
rodadas de estabilidade: cada tela crítica possui somente um dono de rolagem vertical.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from decimal import Decimal, InvalidOperation
from pathlib import Path

import flet as ft

from climatetest_manager import app as legacy_app
from climatetest_manager import production_app
from climatetest_manager.domain.climate_rules import (
    ClimateRuleError,
    available_options,
    resolve_condition,
)
from climatetest_manager.domain.enums import ConditionInputMode
from climatetest_manager.round4_runtime import _force_scroll_top, _safe_settings_builder, _safe_update, _walk
from climatetest_manager.round5_runtime import StableDetailsView
from climatetest_manager.round6_runtime import (
    RefinedNewTestView,
    _card_title,
    _severity_color,
    apply_interaction_polish,
)
from climatetest_manager.ui.components import dialog_banner, styled_dialog
from climatetest_manager.ui.components.table17_interactive import (
    build_interactive_table17,
    matching_row,
    ts_band_label,
)
from climatetest_manager.ui.formatters import format_datetime
from climatetest_manager.ui.theme import AppColors

BUILD_REVISION = "R8-20260814"
TABLE17_MODE = "table17_select"


def _icon_heading(icon: ft.IconData, title: str, subtitle: str = "") -> ft.Row:
    text_controls: list[ft.Control] = [
        ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY)
    ]
    if subtitle:
        text_controls.append(ft.Text(subtitle, size=10, color=AppColors.TEXT_SECONDARY))
    return ft.Row(
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                width=34,
                height=34,
                border_radius=10,
                bgcolor=AppColors.PRIMARY_LIGHT,
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(icon, size=18, color=AppColors.PRIMARY),
            ),
            ft.Column(expand=True, spacing=2, controls=text_controls),
        ],
    )


def _number(value: str) -> Decimal | None:
    cleaned = value.strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


class CleanNewTestView(RefinedNewTestView):
    """Formulário final R7 com resumo e Tabela 17 no mesmo cartão."""

    def __init__(self, *args, **kwargs) -> None:
        self._table_view = "simple"
        self._table17_guide = ft.Container(visible=False)
        self._advanced_holder = ft.Container(visible=False)
        self._simple_holder = ft.Container(visible=True)
        self._simple_button: ft.Button | None = None
        self._advanced_button: ft.Button | None = None
        super().__init__(*args, **kwargs)
        radios = getattr(self.mode_group.content, "controls", None)
        if isinstance(radios, list) and not any(
            isinstance(control, ft.Radio) and control.value == TABLE17_MODE for control in radios
        ):
            radios.append(ft.Radio(value=TABLE17_MODE, label="Selecionar na Tabela 17"))
        self._table17_guide.content = ft.Container(
            border_radius=12,
            bgcolor=AppColors.INFO_LIGHT,
            border=ft.Border.all(1, AppColors.DIVIDER),
            padding=12,
            content=ft.Column(
                spacing=9,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Container(
                                width=24,
                                height=24,
                                border_radius=12,
                                bgcolor=AppColors.PRIMARY,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Text("1", size=10, weight=ft.FontWeight.BOLD, color=AppColors.WHITE),
                            ),
                            ft.Text(
                                "Informe o Ts da amostra",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                        ],
                    ),
                    self.service_temperature,
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Container(
                                width=24,
                                height=24,
                                border_radius=12,
                                bgcolor=AppColors.PRIMARY,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Text("2", size=10, weight=ft.FontWeight.BOLD, color=AppColors.WHITE),
                            ),
                            ft.Text(
                                "Escolha 1 EPL e 1 condição diretamente na tabela abaixo.",
                                expand=True,
                                size=11,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                ],
            ),
        )
        self._on_mode_change()

    def _identity_compact(self) -> ft.Container:
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=16,
            padding=16,
            content=ft.Column(
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    _icon_heading(
                        ft.Icons.BADGE_OUTLINED,
                        "Identificação",
                        "Dados essenciais do ensaio.",
                    ),
                    self.client,
                    self.process_number,
                    self.product,
                    self.sample_quantity,
                ],
            ),
        )

    def _thermal_compact(self) -> ft.Container:
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=16,
            padding=16,
            content=ft.Column(
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    _icon_heading(
                        ft.Icons.THERMOSTAT_OUTLINED,
                        "Configuração térmica",
                        "Escolha como a condição será definida.",
                    ),
                    ft.Container(
                        bgcolor=AppColors.PAGE_BACKGROUND,
                        border_radius=11,
                        border=ft.Border.all(1, AppColors.DIVIDER),
                        padding=10,
                        content=self.mode_group,
                    ),
                    self.epl,
                    self.calculated_fields,
                    self.direct_ts_fields,
                    self.manual_condition_fields,
                    self._table17_guide,
                    self.option_panel,
                ],
            ),
        )

    def _notes_panel(self) -> ft.Container:
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=16,
            padding=14,
            content=ft.Column(
                spacing=9,
                controls=[
                    _icon_heading(ft.Icons.CHAT_BUBBLE_OUTLINE, "Informações complementares"),
                    self.notes,
                ],
            ),
        )

    def _summary_badge(self, label: str, value: str, icon: ft.IconData) -> ft.Container:
        return ft.Container(
            expand=True,
            border_radius=11,
            bgcolor=AppColors.PAGE_BACKGROUND,
            border=ft.Border.all(1, AppColors.DIVIDER),
            padding=11,
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(icon, size=17, color=AppColors.PRIMARY),
                    ft.Column(
                        spacing=1,
                        controls=[
                            ft.Text(label, size=9, color=AppColors.TEXT_SECONDARY),
                            ft.Text(value, size=11, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                        ],
                    ),
                ],
            ),
        )

    def _simple_summary(self) -> ft.Control:
        ts = _number(self.service_temperature.value) if self.mode_group.value in {ConditionInputMode.DIRECT_TS.value, TABLE17_MODE} else (
            self._condition.service_temperature_c if self._condition is not None else None
        )
        epl = self.epl.value or "—"
        option = self.option_group.value or "—"
        band = ts_band_label(self.epl.value, ts)
        return ft.Column(
            spacing=11,
            controls=[
                ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        self._metric(
                            ft.Icons.WATER_DROP_OUTLINED,
                            "Câmara úmida",
                            [
                                ft.Row(
                                    wrap=True,
                                    spacing=12,
                                    controls=[
                                        self.chamber_temperature,
                                        self.chamber_humidity,
                                        self.chamber_duration,
                                    ],
                                ),
                                self.chamber_duration_detail,
                            ],
                        ),
                        self._metric(
                            ft.Icons.AIR,
                            "Secagem",
                            [
                                ft.Row(
                                    wrap=True,
                                    spacing=12,
                                    controls=[self.drying_temperature, self.drying_duration],
                                ),
                                self.drying_duration_detail,
                            ],
                        ),
                    ],
                ),
                ft.Row(
                    spacing=9,
                    controls=[
                        self._summary_badge("EPL", epl, ft.Icons.SHIELD_OUTLINED),
                        self._summary_badge("Faixa de Ts", band, ft.Icons.THERMOSTAT),
                        self._summary_badge(
                            "Configuração",
                            f"Opção {option}" if option != "—" else "—",
                            ft.Icons.CHECK_CIRCLE_OUTLINE,
                        ),
                    ],
                ),
            ],
        )

    def _advanced_table(self) -> ft.Control:
        ts = _number(self.service_temperature.value) if self.mode_group.value in {ConditionInputMode.DIRECT_TS.value, TABLE17_MODE} else (
            self._condition.service_temperature_c if self._condition is not None else None
        )
        return build_interactive_table17(
            ts=ts,
            selected_epl=self.epl.value,
            selected_option=self.option_group.value,
            on_select_epl=self._select_table_epl,
            on_select_option=self._select_table_option,
        )

    def _set_table_view(self, mode: str) -> None:
        self._table_view = mode
        self._simple_holder.visible = mode == "simple"
        self._advanced_holder.visible = mode == "advanced"
        if mode == "advanced":
            self._advanced_holder.content = self._advanced_table()
        if self._simple_button is not None:
            self._simple_button.bgcolor = AppColors.PRIMARY if mode == "simple" else None
            self._simple_button.color = AppColors.WHITE if mode == "simple" else AppColors.PRIMARY
        if self._advanced_button is not None:
            self._advanced_button.bgcolor = AppColors.PRIMARY if mode == "advanced" else None
            self._advanced_button.color = AppColors.WHITE if mode == "advanced" else AppColors.PRIMARY
        _safe_update(self.result_panel)

    def _build_result_panel(self) -> ft.Container:
        self._simple_button = ft.Button(
            content="Visualização simples",
            icon=ft.Icons.DASHBOARD_OUTLINED,
            bgcolor=AppColors.PRIMARY,
            color=AppColors.WHITE,
            on_click=lambda _event: self._set_table_view("simple"),
        )
        self._advanced_button = ft.Button(
            content="Visualização avançada",
            icon=ft.Icons.TABLE_CHART_OUTLINED,
            color=AppColors.PRIMARY,
            on_click=lambda _event: self._set_table_view("advanced"),
        )
        self._simple_holder = ft.Container(content=self._simple_summary())
        self._advanced_holder = ft.Container(visible=False, content=self._advanced_table())
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=16,
            padding=16,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        wrap=True,
                        run_spacing=8,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            _icon_heading(
                                ft.Icons.TUNE,
                                "Condição que será aplicada",
                                "Resumo simples ou conferência direta na Tabela 17.",
                            ),
                            ft.Row(spacing=7, controls=[self._simple_button, self._advanced_button]),
                        ],
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.Container(
                                border_radius=11,
                                bgcolor=AppColors.PRIMARY_LIGHT,
                                border=ft.Border.all(1, AppColors.PRIMARY),
                                padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                                content=self.ts_value,
                            )
                        ],
                    ),
                    self._simple_holder,
                    self._advanced_holder,
                ],
            ),
        )

    def _refresh_result_views(self) -> None:
        if hasattr(self, "_simple_holder"):
            self._simple_holder.content = self._simple_summary()
        if hasattr(self, "_advanced_holder"):
            self._advanced_holder.content = self._advanced_table()
        _safe_update(self.result_panel)

    def _select_table_epl(self, value: str) -> None:
        if _number(self.service_temperature.value) is None:
            self._show_error("Informe o Ts antes de selecionar o EPL na Tabela 17.")
            self._refresh()
            return
        self.epl.value = value
        self.option_group.value = None
        self._recalculate()

    def _select_table_option(self, value: str) -> None:
        ts = _number(self.service_temperature.value)
        if ts is None or not self.epl.value:
            self._show_error("Informe o Ts e selecione o EPL antes da condição.")
            self._refresh()
            return
        permitted = {option.value for option in available_options(self.epl.value, ts)}
        if value not in permitted:
            self._show_error(
                "Esta condição não é permitida para o EPL e o Ts informados. "
                "As opções incompatíveis permanecem acinzentadas."
            )
            self._refresh()
            return
        self.option_group.value = value
        self._recalculate()

    def _on_mode_change(self, _event: object | None = None) -> None:
        mode = self.mode_group.value or ConditionInputMode.CALCULATED.value
        if mode != TABLE17_MODE:
            self._table17_guide.visible = False
            self.epl.visible = True
            super()._on_mode_change(_event)
            return
        self.calculated_fields.visible = False
        self.direct_ts_fields.visible = False
        self.manual_condition_fields.visible = False
        self.option_panel.visible = False
        self.epl.visible = False
        self._table17_guide.visible = True
        self.manual_drying_fields.visible = False
        self._set_table_view("advanced")
        self._recalculate()

    def _recalculate(self, _event: object | None = None) -> None:
        if self.mode_group.value != TABLE17_MODE:
            super()._recalculate(_event)
            self._refresh_result_views()
            return
        self.error_banner.visible = False
        ts = _number(self.service_temperature.value)
        if ts is None:
            self._condition = None
            self.save_button.disabled = True
            self.ts_value.value = "Ts = —"
            self.option_help.value = "Informe o Ts para liberar a Tabela 17."
            self._refresh_result_views()
            self._refresh()
            return
        self.ts_value.value = f"Ts = {str(ts).replace('.', ',')} °C"
        if not self.epl.value:
            self._condition = None
            self.save_button.disabled = True
            self.option_help.value = "Selecione um EPL diretamente na tabela."
            self._refresh_result_views()
            self._refresh()
            return
        try:
            options = {option.value for option in available_options(self.epl.value, ts)}
            if self.option_group.value not in options:
                self._condition = None
                self.save_button.disabled = True
                self.option_help.value = "Agora selecione uma das condições liberadas na tabela."
            else:
                self._condition = resolve_condition(self.epl.value, ts, self.option_group.value)
                self._display_condition(self._condition)
                self.save_button.disabled = False
                self.option_help.value = "Condição selecionada diretamente na Tabela 17."
        except (ClimateRuleError, InvalidOperation, ValueError) as error:
            self._condition = None
            self.save_button.disabled = True
            self._show_error(str(error) or "Revise o Ts e a seleção da Tabela 17.")
        self._refresh_result_views()
        self._refresh()

    def _submit(self, event: object | None = None) -> None:
        if self.mode_group.value != TABLE17_MODE:
            super()._submit(event)
            return
        if self._condition is None or not self.epl.value or not self.option_group.value:
            self._show_error("Informe o Ts e selecione exatamente 1 EPL e 1 condição na Tabela 17.")
            self._refresh()
            return
        original = self.mode_group.value
        self.mode_group.value = ConditionInputMode.DIRECT_TS.value
        try:
            super()._submit(event)
        finally:
            self.mode_group.value = original

    def _build(self) -> ft.Column:
        self._compact_fields()
        top_panels = ft.Row(
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(expand=5, content=self._identity_compact()),
                ft.Container(expand=7, content=self._thermal_compact()),
            ],
        )
        controls: list[ft.Control] = [
            ft.Row(
                wrap=True,
                run_spacing=8,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(
                                "Editar ensaio" if self._details else "Novo ensaio",
                                size=27,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            ft.Text(
                                "Preencha, confira a condição e salve.",
                                size=12,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Button(
                                content="Cancelar",
                                icon=ft.Icons.CLOSE,
                                on_click=lambda _event: self._on_cancel(),
                            ),
                            self.save_button,
                        ],
                    ),
                ],
            ),
            self.error_banner,
            top_panels,
            self._notes_panel(),
        ]
        if self._details:
            controls.append(
                ft.Container(
                    bgcolor=AppColors.SURFACE,
                    border=ft.Border.all(1, AppColors.DIVIDER),
                    border_radius=16,
                    padding=14,
                    content=self.change_reason_selector.control,
                )
            )
        controls.extend([self.result_panel, ft.Container(height=10)])
        return ft.Column(
            key=f"r7-new-test-{id(self)}",
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=controls,
        )


def _contains_text(control: ft.Control, needle: str) -> bool:
    return any(
        isinstance(item, ft.Text) and needle.casefold() in str(item.value or "").casefold()
        for item in _walk(control)
    )


def _strip_duplicate_danger_actions(panel: ft.Control) -> ft.Control:
    content = getattr(panel, "content", None)
    controls = getattr(content, "controls", None)
    if not isinstance(controls, list):
        return panel
    kept: list[ft.Control] = []
    for control in controls:
        if _contains_text(control, "Cancelar este ensaio") or _contains_text(control, "Excluir cadastro"):
            continue
        if isinstance(control, ft.Divider) and (not kept or isinstance(kept[-1], ft.Divider)):
            continue
        kept.append(control)
    while kept and isinstance(kept[-1], ft.Divider):
        kept.pop()
    content.controls = kept
    return panel


def _hold_control(
    page: ft.Page,
    *,
    label: str,
    on_confirm,
    enabled: Callable[[], bool] | None = None,
) -> ft.Control:
    progress = ft.ProgressBar(value=0, height=8, color=AppColors.DANGER, bgcolor=AppColors.DANGER_LIGHT)
    text = ft.Text(label, size=11, weight=ft.FontWeight.BOLD, color=AppColors.DANGER)
    state = {"holding": False, "generation": 0}

    async def advance(generation: int) -> None:
        for step in range(1, 21):
            await asyncio.sleep(0.07)
            if not state["holding"] or state["generation"] != generation:
                return
            progress.value = step / 20
            with suppress(RuntimeError):
                progress.update()
        state["holding"] = False
        if enabled is not None and not enabled():
            progress.value = 0
            with suppress(RuntimeError):
                progress.update()
            return
        on_confirm()

    def down(_event: object | None = None) -> None:
        state["generation"] += 1
        state["holding"] = True
        progress.value = 0
        page.run_task(advance, state["generation"])

    def release(_event: object | None = None) -> None:
        state["holding"] = False
        state["generation"] += 1
        progress.value = 0
        with suppress(RuntimeError):
            progress.update()

    return ft.GestureDetector(
        on_tap_down=down,
        on_tap_up=release,
        on_tap_cancel=release,
        content=ft.Container(
            border=ft.Border.all(1, AppColors.DANGER),
            border_radius=12,
            padding=12,
            bgcolor=AppColors.DANGER_LIGHT,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[text, ft.Text("Segure por 1,4 s", size=9, color=AppColors.TEXT_SECONDARY)],
                    ),
                    progress,
                ],
            ),
        ),
    )


class CleanDetailsView(StableDetailsView):
    """Detalhes sem banners técnicos e com um único menu de ações."""

    def __init__(
        self,
        details,
        *,
        on_back,
        on_edit,
        on_admin_delete,
        is_admin: bool,
        can_operate: bool,
        **kwargs,
    ) -> None:
        self._r7_on_edit = on_edit
        self._r7_on_admin_delete = on_admin_delete
        self._r7_is_admin = is_admin
        self._r7_can_operate = can_operate
        super().__init__(details, on_back=on_back, on_edit=on_edit, **kwargs)
        operational = _strip_duplicate_danger_actions(self._action_panel())
        if not can_operate:
            operational = ft.Container(
                border_radius=12,
                bgcolor=AppColors.PAGE_BACKGROUND,
                padding=14,
                content=ft.Text(
                    "Perfil de consulta: ações operacionais ficam indisponíveis.",
                    color=AppColors.TEXT_SECONDARY,
                ),
            )
        actions_button = ft.Button(
            content="Ações",
            icon=ft.Icons.MORE_HORIZ,
            on_click=self._show_actions_menu,
        )
        self._r7_actions_button = actions_button
        self.root = ft.Column(
            key=f"r7-details-{details.id}-{id(self)}",
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(
                    wrap=True,
                    run_spacing=8,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=10,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK,
                                    tooltip="Voltar para Ensaios",
                                    on_click=lambda _event: on_back(),
                                ),
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text(
                                            f"{details.client} / {details.process_number}",
                                            size=26,
                                            weight=ft.FontWeight.BOLD,
                                            color=AppColors.TEXT_PRIMARY,
                                        ),
                                        ft.Text(f"Ensaio #{details.id}", size=12, color=AppColors.TEXT_SECONDARY),
                                    ],
                                ),
                            ],
                        ),
                        actions_button,
                    ],
                ),
                self._summary_panel(),
                self._journey_panel(),
                self._phase_panel(),
                operational,
                self._history_panel(),
                ft.Container(height=12),
            ],
        )

    def _action_tile(
        self,
        *,
        title: str,
        description: str,
        icon: ft.IconData,
        enabled: bool,
        tooltip: str,
        on_click,
        danger: bool = False,
    ) -> ft.Container:
        button = ft.Button(
            content=title,
            icon=icon,
            disabled=not enabled,
            color=AppColors.DANGER if danger and enabled else None,
            on_click=(lambda _event: on_click()) if enabled else None,
        )
        return ft.Container(
            tooltip=tooltip if not enabled else None,
            opacity=1 if enabled else 0.48,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=12,
            padding=12,
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Container(expand=True, content=ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(title, size=12, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
                            ft.Text(description, size=10, color=AppColors.TEXT_SECONDARY),
                        ],
                    )),
                    button,
                ],
            ),
        )

    def _show_actions_menu(self, _event: object | None = None) -> None:
        page = self._r7_actions_button.page
        details = self._details
        active = details.situation in {"Aguardando", "Na Câmara", "Em Secagem"}

        def close_then(callback) -> None:
            page.pop_dialog()
            callback()

        items = [
            self._action_tile(
                title="Editar dados",
                description="Corrigir cadastro e parâmetros com rastreabilidade.",
                icon=ft.Icons.EDIT_OUTLINED,
                enabled=self._r7_can_operate,
                tooltip="Este perfil possui acesso somente para consulta.",
                on_click=lambda: close_then(self._r7_on_edit),
            ),
            self._action_tile(
                title="Cancelar ensaio",
                description="Interromper o ensaio mantendo o registro no histórico.",
                icon=ft.Icons.CANCEL_OUTLINED,
                enabled=bool(self._r7_can_operate and active),
                tooltip=(
                    "Este ensaio já está encerrado."
                    if not active
                    else "Este perfil possui acesso somente para consulta."
                ),
                on_click=lambda: close_then(self._show_r7_cancel_dialog),
                danger=True,
            ),
            self._action_tile(
                title="Excluir do histórico",
                description="Remover o cadastro da operação mantendo auditoria da exclusão.",
                icon=ft.Icons.DELETE_FOREVER_OUTLINED,
                enabled=self._r7_is_admin,
                tooltip="Somente administradores podem realizar esta ação.",
                on_click=lambda: close_then(self._show_r7_delete_dialog),
                danger=True,
            ),
        ]
        page.show_dialog(
            apply_interaction_polish(
                styled_dialog(
                    title="Ações do ensaio",
                    subtitle="Escolha somente a ação que deseja realizar",
                    icon=ft.Icons.TUNE,
                    content=ft.Column(width=620, tight=True, spacing=9, controls=items),
                    actions=[ft.Button(content="Fechar", on_click=lambda _close: page.pop_dialog())],
                )
            )
        )

    def _show_r7_cancel_dialog(self) -> None:
        page = self._r7_actions_button.page
        reason = ft.TextField(
            label="Motivo do cancelamento *",
            hint_text="Resuma por que o ensaio está sendo cancelado.",
            multiline=True,
            min_lines=2,
            max_lines=4,
            max_length=500,
        )
        error = ft.Text("", size=10, color=AppColors.DANGER)

        def valid() -> bool:
            value = reason.value.strip()
            if len(value) < 8:
                reason.error = "Informe um motivo com pelo menos 8 caracteres."
                _safe_update(reason)
                return False
            return True

        def confirm() -> None:
            if not valid():
                return
            page.pop_dialog()
            self._on_cancel(reason.value.strip())

        page.show_dialog(
            apply_interaction_polish(
                styled_dialog(
                    title="Cancelar ensaio",
                    subtitle="O cancelamento será mantido no histórico",
                    icon=ft.Icons.WARNING_AMBER,
                    danger=True,
                    content=ft.Column(
                        width=560,
                        tight=True,
                        spacing=11,
                        controls=[
                            reason,
                            dialog_banner(
                                "Depois de informar o motivo, pressione e segure para confirmar.",
                                danger=True,
                            ),
                            _hold_control(page, label="Pressione e segure para cancelar", on_confirm=confirm),
                            error,
                        ],
                    ),
                    actions=[ft.TextButton(content="Voltar", on_click=lambda _close: page.pop_dialog())],
                )
            )
        )

    def _show_r7_delete_dialog(self) -> None:
        page = self._r7_actions_button.page
        reason = ft.TextField(
            label="Motivo da exclusão *",
            hint_text="Ex.: cadastro fictício, duplicado ou inválido.",
            multiline=True,
            min_lines=2,
            max_lines=4,
            max_length=500,
        )

        def valid() -> bool:
            value = reason.value.strip()
            if len(value) < 10:
                reason.error = "Informe um motivo com pelo menos 10 caracteres."
                _safe_update(reason)
                return False
            return True

        def confirm() -> None:
            if not valid():
                return
            page.pop_dialog()
            self._r7_on_admin_delete(reason.value.strip())

        page.show_dialog(
            apply_interaction_polish(
                styled_dialog(
                    title="Excluir do histórico",
                    subtitle="Ação restrita ao administrador",
                    icon=ft.Icons.DELETE_FOREVER_OUTLINED,
                    danger=True,
                    content=ft.Column(
                        width=560,
                        tight=True,
                        spacing=11,
                        controls=[
                            reason,
                            dialog_banner(
                                "A exclusão remove o ensaio da operação, mas a auditoria da ação permanece.",
                                danger=True,
                            ),
                            _hold_control(page, label="Pressione e segure para excluir", on_confirm=confirm),
                        ],
                    ),
                    actions=[ft.TextButton(content="Voltar", on_click=lambda _close: page.pop_dialog())],
                )
            )
        )


def _incident_log_card_r7(incident, *, on_resolve, close_log, on_refresh) -> ft.Container:
    is_open = incident.status == "open"
    controls: list[ft.Control] = [
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text(f"#{incident.id} • {incident.category}", size=12, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "Não resolvida" if is_open else "Resolvida",
                    size=9,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.DANGER if is_open else AppColors.PRIMARY,
                ),
            ],
        ),
        ft.Text(
            f"{incident.severity} • {format_datetime(incident.reported_at, assume_utc=True)}",
            size=9,
            color=_severity_color(incident.severity),
        ),
        ft.Text(incident.description, size=10, color=AppColors.TEXT_PRIMARY),
    ]
    if is_open and callable(on_resolve):
        button = ft.Button(content="Marcar como resolvida", icon=ft.Icons.CHECK_CIRCLE_OUTLINE)

        def show_resolution(_event: object | None = None) -> None:
            page = button.page
            note = ft.TextField(
                label="Observação sobre a solução (opcional)",
                multiline=True,
                min_lines=2,
                max_lines=4,
                max_length=1000,
            )
            error = ft.Text("", size=10, color=AppColors.DANGER)

            def finish(_confirm: object | None = None) -> None:
                note_value = note.value.strip()
                action = "Falha marcada como resolvida após confirmação do administrador."
                if note_value:
                    action += f" Observação: {note_value}"
                result = on_resolve(incident.id, action)
                if result and "já foi encerrada" not in str(result).casefold():
                    error.value = str(result)
                    _safe_update(error)
                    return
                with suppress(Exception):
                    page.pop_dialog()
                close_log()
                on_refresh()

            page.show_dialog(
                apply_interaction_polish(
                    styled_dialog(
                        title=f"A falha #{incident.id} foi resolvida?",
                        subtitle="A observação é opcional",
                        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                        content=ft.Column(width=500, tight=True, spacing=10, controls=[note, error]),
                        actions=[
                            ft.TextButton(content="Manter aberta", on_click=lambda _close: page.pop_dialog()),
                            ft.Button(
                                content="Marcar resolvida",
                                bgcolor=AppColors.PRIMARY,
                                color=AppColors.WHITE,
                                on_click=finish,
                            ),
                        ],
                    )
                )
            )

        button.on_click = show_resolution
        controls.append(button)
    return ft.Container(
        border=ft.Border.all(1, AppColors.DIVIDER),
        border_radius=12,
        bgcolor=AppColors.PAGE_BACKGROUND,
        padding=12,
        content=ft.Column(spacing=6, controls=controls),
    )


def _compact_incident_panel_r7(**kwargs) -> ft.Control:
    incidents = list(kwargs.get("system_incidents") or [])
    on_report = kwargs.get("on_report_system_incident")
    on_resolve = kwargs.get("on_resolve_system_incident")
    on_refresh = kwargs["on_refresh"]
    open_count = sum(item.status == "open" for item in incidents)
    resolved_count = len(incidents) - open_count
    report_button = ft.Button(content="Registrar falha", icon=ft.Icons.ADD_CIRCLE_OUTLINE)
    log_button = ft.Button(content="Abrir log de falhas", icon=ft.Icons.RECEIPT_LONG_OUTLINED)

    def report(_event: object | None = None) -> None:
        if not callable(on_report):
            return
        page = report_button.page
        description = ft.TextField(
            label="O que aconteceu?",
            multiline=True,
            min_lines=3,
            max_lines=5,
            max_length=2000,
        )
        immediate = ft.TextField(
            label="Ação imediata (opcional)",
            multiline=True,
            min_lines=2,
            max_lines=3,
            max_length=1000,
        )
        error = ft.Text("", size=10, color=AppColors.DANGER)

        def save(_confirm: object | None = None) -> None:
            if len(description.value.strip()) < 10:
                description.error = "Descreva a falha com pelo menos 10 caracteres."
                _safe_update(description)
                return
            action = immediate.value.strip() or "Falha registrada para avaliação da equipe responsável."
            result = on_report("other", description.value.strip(), action)
            if result:
                error.value = str(result)
                _safe_update(error)
                return
            page.pop_dialog()
            on_refresh()

        page.show_dialog(
            apply_interaction_polish(
                styled_dialog(
                    title="Registrar falha",
                    subtitle="O alerta interno e o e-mail são disparados após o registro",
                    icon=ft.Icons.BUG_REPORT_OUTLINED,
                    content=ft.Column(width=560, tight=True, spacing=10, controls=[description, immediate, error]),
                    actions=[
                        ft.TextButton(content="Cancelar", on_click=lambda _close: page.pop_dialog()),
                        ft.Button(content="Registrar", bgcolor=AppColors.PRIMARY, color=AppColors.WHITE, on_click=save),
                    ],
                )
            )
        )

    def show_log(_event: object | None = None) -> None:
        page = log_button.page
        log_open = {"value": True}

        def close_log() -> None:
            if not log_open["value"]:
                return
            log_open["value"] = False
            with suppress(Exception):
                page.pop_dialog()

        cards = [
            _incident_log_card_r7(
                incident,
                on_resolve=on_resolve,
                close_log=close_log,
                on_refresh=on_refresh,
            )
            for incident in incidents
        ] or [ft.Text("Nenhuma falha registrada.", color=AppColors.TEXT_SECONDARY)]
        page.show_dialog(
            apply_interaction_polish(
                styled_dialog(
                    title="Log de falhas",
                    subtitle=f"{open_count} não resolvida(s) • {resolved_count} resolvida(s)",
                    icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                    content=ft.Container(
                        width=700,
                        height=480,
                        content=ft.Column(scroll=ft.ScrollMode.AUTO, spacing=8, controls=cards),
                    ),
                    actions=[ft.Button(content="Fechar", on_click=lambda _close: close_log())],
                )
            )
        )

    report_button.on_click = report
    log_button.on_click = show_log
    return ft.Column(
        spacing=11,
        controls=[
            _icon_heading(
                ft.Icons.GPP_MAYBE_OUTLINED,
                "Falhas do sistema e ações corretivas",
                "Resumo das ocorrências registradas.",
            ),
            ft.Row(
                spacing=8,
                wrap=True,
                controls=[
                    ft.Container(
                        border_radius=10,
                        bgcolor=AppColors.DANGER_LIGHT if open_count else AppColors.PRIMARY_LIGHT,
                        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                        content=ft.Text(
                            f"{open_count} não resolvida(s)",
                            size=10,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.DANGER if open_count else AppColors.PRIMARY,
                        ),
                    ),
                    ft.Container(
                        border_radius=10,
                        bgcolor=AppColors.PAGE_BACKGROUND,
                        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                        content=ft.Text(f"{resolved_count} resolvida(s)", size=10),
                    ),
                ],
            ),
            ft.Row(spacing=8, controls=[report_button, log_button]),
        ],
    )


def _settings_builder(**kwargs) -> ft.Control:
    content = _safe_settings_builder(**kwargs)
    if not isinstance(content, ft.Column):
        return apply_interaction_polish(content)
    for control in list(content.controls):
        if isinstance(control, ft.Container) and _contains_text(control, "Falhas do sistema e ações corretivas"):
            control.padding = 16
            control.content = _compact_incident_panel_r7(**kwargs)
        elif isinstance(control, ft.Container):
            control.padding = 16
    hide_prefixes = (
        "Remetente:",
        "Destinatários automáticos:",
        "Destinatários do teste:",
        "O envio usa a mesma tarefa",
        "Banco monitorado:",
        "Última verificação:",
        "O servidor, os e-mails e os backups",
    )
    for item in _walk(content):
        if isinstance(item, ft.Text):
            value = str(item.value or "")
            if value.startswith(hide_prefixes):
                item.visible = False
    return apply_interaction_polish(content)


async def _configure_backup_directory(self, _event: object | None = None) -> None:
    if legacy_app._server_mode() and not legacy_app._local_server_client(self._page):
        self._show_message(
            "A pasta de backup deve ser escolhida no próprio computador servidor.",
            error=True,
        )
        return
    try:
        path = await ft.FilePicker().get_directory_path(
            dialog_title="Escolha a pasta dos backups automáticos"
        )
    except Exception as error:
        self._show_message(
            f"O seletor de pastas do Windows não pôde ser aberto: {error}",
            error=True,
        )
        return
    if not path:
        return
    try:
        production_app.save_storage_settings(production_app.get_database_path().parent, Path(path))
        production_app.create_configured_database_backups(production_app.get_database_path())
    except (OSError, ValueError) as error:
        self._show_message(str(error), error=True)
        return
    self.show_settings()
    self._show_message("Pasta de backup atualizada e primeira cópia criada.")


def _show_new_test(self) -> None:
    if not self._current_user.can_operate:
        self._show_message("Este perfil possui acesso somente para consulta.", error=True)
        return
    if self._selected_view == "new_test" and self._new_test_view is not None:
        return
    self._prepare_theme()
    view = CleanNewTestView(
        on_cancel=self._confirm_discard_new_test,
        on_save=self._save_test,
        draft=self._new_test_draft,
    )
    view.save_button.disabled = False
    self._new_test_view = view
    self._render(view.root, selected_view="new_test")
    self._page.run_task(_force_scroll_top, view.root)


def _show_edit_test(self, test_id: int) -> None:
    if not self._current_user.can_operate:
        self._show_message("Este perfil possui acesso somente para consulta.", error=True)
        return
    self._prepare_theme()
    view = CleanNewTestView(
        on_cancel=lambda: self.show_details(test_id),
        on_save=lambda command: self._update_test(test_id, command),
        details=self._service.get_details(test_id),
    )
    view.save_button.disabled = False
    self._render(view.root, selected_view="details")
    self._page.run_task(_force_scroll_top, view.root)


def _show_details(self, test_id: int) -> None:
    self._prepare_theme()
    self._active_test_id = test_id
    details = self._service.get_details(test_id)
    view = CleanDetailsView(
        details,
        on_back=self.show_tests,
        on_start_chamber=lambda value: self._perform(
            test_id,
            lambda: self._service.start_chamber(test_id, value),
            "Câmara iniciada e prazos calculados.",
        ),
        on_start_drying=lambda value: self._perform(
            test_id,
            lambda: self._service.start_drying(test_id, value),
            "Secagem iniciada a partir do horário real.",
        ),
        on_finish=lambda value: self._perform(
            test_id,
            lambda: self._service.finish(test_id, value),
            "Ensaio finalizado.",
        ),
        on_cancel=lambda reason: self._perform(
            test_id,
            lambda: self._service.cancel(test_id, reason),
            "Ensaio cancelado e motivo registrado.",
        ),
        on_edit=lambda: self.show_edit_test(test_id),
        on_delete=lambda: self._delete_test(test_id),
        on_admin_delete=lambda reason: self._delete_test_as_admin(test_id, reason),
        is_admin=self._current_user.is_admin,
        can_operate=self._current_user.can_operate,
        on_change_timestamp=lambda timestamp, value, reason: self._perform(
            test_id,
            lambda: self._service.change_operational_timestamp(test_id, timestamp, value, reason),
            "Horário operacional corrigido e alteração registrada.",
        ),
        on_advance_for_testing=(
            (
                lambda: self._perform(
                    test_id,
                    lambda: self._service.advance_for_testing(test_id),
                    "Etapa avançada somente para validação.",
                )
            )
            if production_app.test_controls_enabled()
            else None
        ),
    )
    self._render(view.root, selected_view="details")
    self._page.run_task(_force_scroll_top, view.root)


def _animated_screen_switcher() -> ft.AnimatedSwitcher:
    return ft.AnimatedSwitcher(
        content=ft.Container(expand=True),
        duration=180,
        reverse_duration=140,
        transition=ft.AnimatedSwitcherTransition.FADE,
        switch_in_curve=ft.AnimationCurve.EASE_OUT_CUBIC,
        switch_out_curve=ft.AnimationCurve.EASE_IN_CUBIC,
        expand=True,
    )


_App = production_app.ProductionClimateTestApplication
_original_launcher_open = production_app.ProductionClimateTestLauncher._open_application


def _open_application_with_welcome(self, user) -> None:
    _original_launcher_open(self, user)
    first = user.first_name.strip() or user.full_name
    self._page.show_dialog(
        ft.SnackBar(
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.WAVING_HAND_OUTLINED, color=AppColors.WHITE),
                    ft.Text(f"Bem-vindo de volta, {first}.", color=AppColors.WHITE),
                ],
            ),
            bgcolor=AppColors.PRIMARY,
            duration=2200,
        )
    )


def install_round7_fixes() -> None:
    if getattr(production_app, "_round7_fixes_installed", False):
        return
    legacy_app._screen_switcher = _animated_screen_switcher
    _App.show_new_test = _show_new_test
    _App.show_edit_test = _show_edit_test
    _App.show_details = _show_details
    _App._configure_backup_directory = _configure_backup_directory
    production_app.build_production_settings_view = _settings_builder
    production_app.ProductionClimateTestLauncher._open_application = _open_application_with_welcome
    production_app._round7_fixes_installed = True


install_round7_fixes()
main = production_app.main
