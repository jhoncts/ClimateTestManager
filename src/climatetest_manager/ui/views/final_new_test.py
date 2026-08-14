"""Cadastro final de ensaios com layout compacto e árvore visual estável.

Esta tela não herda as composições das rodadas de refinamento. Somente a regra de
negócio e os controles-base validados são reutilizados. Cada controle aparece uma
única vez na árvore do Flet, evitando o desaparecimento de cards no WebView2.
"""

from __future__ import annotations

from contextlib import suppress
from decimal import Decimal, InvalidOperation

import flet as ft

from climatetest_manager.domain.climate_rules import (
    ClimateRuleError,
    available_options,
    resolve_condition,
)
from climatetest_manager.domain.enums import ConditionInputMode
from climatetest_manager.ui.components.table17_interactive import (
    InteractiveTable17,
    build_interactive_table17,
    ts_band_label,
)
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.ui.views.new_test import NewTestView

TABLE17_MODE = "table17_select"


def _number(value: str) -> Decimal | None:
    cleaned = value.strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        parsed = Decimal(cleaned)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def _safe_update(control: ft.Control | None) -> None:
    if control is None:
        return
    with suppress(RuntimeError):
        control.update()


def _section_heading(
    icon: ft.IconData,
    title: str,
    subtitle: str = "",
) -> ft.Row:
    text: list[ft.Control] = [
        ft.Text(
            title,
            size=14,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )
    ]
    if subtitle:
        text.append(ft.Text(subtitle, size=9, color=AppColors.TEXT_SECONDARY))
    return ft.Row(
        spacing=9,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                width=32,
                height=32,
                border_radius=9,
                bgcolor=AppColors.PRIMARY_LIGHT,
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(icon, size=17, color=AppColors.PRIMARY),
            ),
            ft.Column(expand=True, spacing=1, controls=text),
        ],
    )


def _selection_badge(label: str, value: ft.Text, icon: ft.IconData) -> ft.Container:
    return ft.Container(
        expand=True,
        border_radius=10,
        bgcolor=AppColors.PAGE_BACKGROUND,
        border=ft.Border.all(1, AppColors.DIVIDER),
        padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        content=ft.Row(
            spacing=7,
            controls=[
                ft.Icon(icon, size=16, color=AppColors.PRIMARY),
                ft.Column(
                    spacing=0,
                    controls=[
                        ft.Text(label, size=8, color=AppColors.TEXT_SECONDARY),
                        value,
                    ],
                ),
            ],
        ),
    )


class FinalNewTestView(NewTestView):
    """Formulário compacto, dinâmico e estável para cadastro e edição."""

    _interactive_table: InteractiveTable17

    def __init__(self, *args, **kwargs) -> None:
        self._table_view = "simple"
        self._simple_holder = ft.Container(visible=True)
        self._advanced_holder = ft.Container(visible=False)
        self._table17_guide = ft.Container(visible=False)
        self._notes_count = ft.Text("0/1000", size=8, color=AppColors.TEXT_SECONDARY)
        self._simple_button: ft.Button | None = None
        self._advanced_button: ft.Button | None = None
        super().__init__(*args, **kwargs)

        self.notes.min_lines = 1
        self.notes.max_lines = 3
        self.notes.max_length = 1000
        self.notes.hint_text = "Digite observações sobre o ensaio (opcional)..."
        self._notes_count.value = f"{len(self.notes.value or '')}/1000"
        previous_notes_change = self.notes.on_change

        def update_notes_count(event: object | None = None) -> None:
            if previous_notes_change is not None:
                previous_notes_change(event)
            self._notes_count.value = f"{len(self.notes.value or '')}/1000"
            _safe_update(self._notes_count)

        self.notes.on_change = update_notes_count
        self.save_button.disabled = False
        self.save_button.bgcolor = AppColors.PRIMARY
        self.save_button.color = AppColors.WHITE

        for field in (self.client, self.process_number, self.product, self.sample_quantity):
            previous = field.on_change

            def clear_error(event, *, control=field, callback=previous) -> None:
                control.error = None
                if callback is not None:
                    callback(event)

            field.on_change = clear_error

        self._refresh_targets = (
            *self._refresh_targets,
            self._table17_guide,
            self._simple_holder,
            self._advanced_holder,
        )
        self._on_mode_change()

    def _prepare_controls(self) -> None:
        for field in (
            self.client,
            self.process_number,
            self.product,
            self.sample_quantity,
            self.tamb,
            self.delta_t,
            self.service_temperature,
            self.ts_reference,
            self.manual_chamber_temperature,
            self.manual_chamber_humidity,
            self.manual_chamber_duration,
            self.manual_drying_temperature,
            self.manual_drying_duration,
        ):
            field.height = 44
            field.dense = True

        self.epl.height = 44
        self.epl.dense = True

        radios = list(getattr(self.mode_group.content, "controls", []) or [])
        if not any(
            isinstance(control, ft.Radio) and control.value == TABLE17_MODE for control in radios
        ):
            radios.append(ft.Radio(value=TABLE17_MODE, label="Selecionar na Tabela 17"))
        self.mode_group.content = ft.Column(spacing=2, controls=radios)

        self._table17_guide.content = ft.Container(
            border_radius=11,
            bgcolor=AppColors.INFO_LIGHT,
            border=ft.Border.all(1, AppColors.DIVIDER),
            padding=10,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            self._step_number("1"),
                            ft.Text(
                                "Informe o Ts da amostra no campo acima.",
                                expand=True,
                                size=10,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        controls=[
                            self._step_number("2"),
                            ft.Text(
                                "Selecione o EPL e a condição diretamente na tabela abaixo.",
                                expand=True,
                                size=10,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                ],
            ),
        )

    @staticmethod
    def _step_number(value: str) -> ft.Container:
        return ft.Container(
            width=23,
            height=23,
            border_radius=12,
            bgcolor=AppColors.PRIMARY,
            alignment=ft.Alignment.CENTER,
            content=ft.Text(
                value,
                size=9,
                weight=ft.FontWeight.BOLD,
                color=AppColors.WHITE,
            ),
        )

    def _identity_panel(self) -> ft.Container:
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=14,
            padding=14,
            content=ft.Column(
                spacing=9,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    _section_heading(
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

    def _thermal_panel(self) -> ft.Container:
        input_area = ft.Column(
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                self.epl,
                self.calculated_fields,
                self.direct_ts_fields,
                self.manual_condition_fields,
                self._table17_guide,
            ],
        )
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=14,
            padding=14,
            content=ft.Column(
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    _section_heading(
                        ft.Icons.THERMOSTAT_OUTLINED,
                        "Configuração térmica",
                        "Escolha como a condição será definida.",
                    ),
                    ft.ResponsiveRow(
                        spacing=12,
                        run_spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Container(
                                col={"xs": 12, "sm": 5},
                                border_radius=11,
                                bgcolor=AppColors.PAGE_BACKGROUND,
                                border=ft.Border.all(1, AppColors.DIVIDER),
                                padding=10,
                                content=self.mode_group,
                            ),
                            ft.Container(
                                col={"xs": 12, "sm": 7},
                                content=input_area,
                            ),
                        ],
                    ),
                    self.option_panel,
                ],
            ),
        )

    def _notes_panel(self) -> ft.Container:
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=14,
            padding=12,
            content=ft.Column(
                spacing=8,
                controls=[
                    _section_heading(
                        ft.Icons.CHAT_BUBBLE_OUTLINE,
                        "Informações complementares",
                    ),
                    self.notes,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[self._notes_count],
                    ),
                ],
            ),
        )

    def _metric(
        self,
        icon: ft.IconData,
        title: str,
        controls: list[ft.Control],
    ) -> ft.Container:
        return ft.Container(
            expand=True,
            bgcolor=AppColors.PAGE_BACKGROUND,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=12,
            padding=12,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Container(
                                width=30,
                                height=30,
                                border_radius=9,
                                bgcolor=AppColors.PRIMARY_LIGHT,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(icon, size=16, color=AppColors.PRIMARY),
                            ),
                            ft.Text(
                                title,
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                        ],
                    ),
                    *controls,
                ],
            ),
        )

    def _simple_summary(self) -> ft.Control:
        self._simple_epl = ft.Text(
            "—", size=10, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY
        )
        self._simple_band = ft.Text(
            "Aguardando seleção",
            size=10,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )
        self._simple_option = ft.Text(
            "—", size=10, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY
        )
        self._simple_source = ft.Text(
            "Aguardando condição",
            size=10,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )
        return ft.Column(
            spacing=10,
            controls=[
                ft.ResponsiveRow(
                    spacing=10,
                    run_spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Container(
                            col={"xs": 12, "md": 6},
                            content=self._metric(
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
                        ),
                        ft.Container(
                            col={"xs": 12, "md": 6},
                            content=self._metric(
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
                        ),
                    ],
                ),
                ft.ResponsiveRow(
                    spacing=8,
                    controls=[
                        ft.Container(
                            col={"xs": 6, "md": 3},
                            content=_selection_badge(
                                "EPL", self._simple_epl, ft.Icons.SHIELD_OUTLINED
                            ),
                        ),
                        ft.Container(
                            col={"xs": 6, "md": 3},
                            content=_selection_badge(
                                "Faixa de Ts", self._simple_band, ft.Icons.THERMOSTAT
                            ),
                        ),
                        ft.Container(
                            col={"xs": 6, "md": 3},
                            content=_selection_badge(
                                "Configuração",
                                self._simple_option,
                                ft.Icons.CHECK_CIRCLE_OUTLINE,
                            ),
                        ),
                        ft.Container(
                            col={"xs": 6, "md": 3},
                            content=_selection_badge(
                                "Condição aplicada",
                                self._simple_source,
                                ft.Icons.DESCRIPTION_OUTLINED,
                            ),
                        ),
                    ],
                ),
            ],
        )

    def _advanced_table(self) -> InteractiveTable17:
        return build_interactive_table17(
            ts=self._current_ts(),
            selected_epl=self.epl.value,
            selected_option=self.option_group.value,
            on_select_epl=self._select_table_epl,
            on_select_option=self._select_table_option,
            on_invalid=self._show_table_error,
        )

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
        self._interactive_table = self._advanced_table()
        self._advanced_holder = ft.Container(visible=False, content=self._interactive_table)
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.PRIMARY),
            border_radius=14,
            padding=14,
            content=ft.Column(
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Row(
                        wrap=True,
                        run_spacing=8,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            _section_heading(
                                ft.Icons.TUNE,
                                "Condição que será aplicada",
                                "Resumo operacional antes de salvar o cadastro.",
                            ),
                            ft.Row(
                                spacing=6,
                                controls=[self._simple_button, self._advanced_button],
                            ),
                        ],
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.Container(
                                border_radius=10,
                                bgcolor=AppColors.PRIMARY_LIGHT,
                                border=ft.Border.all(1, AppColors.PRIMARY),
                                padding=ft.Padding.symmetric(horizontal=11, vertical=6),
                                content=self.ts_value,
                            )
                        ],
                    ),
                    self._simple_holder,
                    self._advanced_holder,
                ],
            ),
        )

    def _build(self) -> ft.Column:
        self._prepare_controls()
        controls: list[ft.Control] = [
            ft.Row(
                wrap=True,
                run_spacing=8,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=1,
                        controls=[
                            ft.Text(
                                "Editar ensaio" if self._details else "Novo ensaio",
                                size=26,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            ft.Text(
                                "Preencha as informações abaixo para configurar o ensaio.",
                                size=11,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=7,
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
            ft.ResponsiveRow(
                spacing=12,
                run_spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Container(
                        col={"xs": 12, "md": 5},
                        content=self._identity_panel(),
                    ),
                    ft.Container(
                        col={"xs": 12, "md": 7},
                        content=self._thermal_panel(),
                    ),
                ],
            ),
            self._notes_panel(),
        ]
        if self._details:
            controls.append(
                ft.Container(
                    bgcolor=AppColors.SURFACE,
                    border=ft.Border.all(1, AppColors.DIVIDER),
                    border_radius=14,
                    padding=14,
                    content=self.change_reason_selector.control,
                )
            )
        controls.extend([self.result_panel, ft.Container(height=8)])
        return ft.Column(
            key=f"final-new-test-{id(self)}",
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=controls,
        )

    def _current_ts(self) -> Decimal | None:
        if self.mode_group.value in {ConditionInputMode.DIRECT_TS.value, TABLE17_MODE}:
            return _number(self.service_temperature.value)
        if self._condition is not None:
            return self._condition.service_temperature_c
        return None

    def _set_table_view(self, mode: str) -> None:
        self._table_view = "advanced" if mode == "advanced" else "simple"
        self._simple_holder.visible = self._table_view == "simple"
        self._advanced_holder.visible = self._table_view == "advanced"
        if self._simple_button is not None:
            self._simple_button.bgcolor = (
                AppColors.PRIMARY if self._table_view == "simple" else None
            )
            self._simple_button.color = (
                AppColors.WHITE if self._table_view == "simple" else AppColors.PRIMARY
            )
        if self._advanced_button is not None:
            self._advanced_button.bgcolor = (
                AppColors.PRIMARY if self._table_view == "advanced" else None
            )
            self._advanced_button.color = (
                AppColors.WHITE if self._table_view == "advanced" else AppColors.PRIMARY
            )
        _safe_update(self.result_panel if hasattr(self, "result_panel") else None)

    def _refresh_result_views(self) -> None:
        if not hasattr(self, "_interactive_table"):
            return
        ts = self._current_ts()
        epl = self.epl.value or "—"
        option = self.option_group.value or "—"
        self._simple_epl.value = epl
        self._simple_band.value = ts_band_label(self.epl.value, ts)
        self._simple_option.value = f"Opção {option}" if option != "—" else "—"
        if self._condition is None:
            self._simple_source.value = "Aguardando condição"
        elif self._condition.rule_id == "DIRECT-CONFIGURATION":
            self._simple_source.value = "Configuração personalizada"
        else:
            self._simple_source.value = f"Tabela 17 • {self._condition.rule_id}"
        self._interactive_table.set_state(
            ts=ts,
            selected_epl=self.epl.value,
            selected_option=self.option_group.value,
        )

    def _show_table_error(self, message: str) -> None:
        self._show_error(message)
        self._refresh()

    def _select_table_epl(self, value: str) -> None:
        ts = _number(self.service_temperature.value)
        if ts is None:
            self._show_table_error("Informe o Ts antes de selecionar o EPL na Tabela 17.")
            return
        self.epl.value = value
        self.option_group.value = None
        self._recalculate()

    def _select_table_option(self, value: str) -> None:
        ts = _number(self.service_temperature.value)
        if ts is None or not self.epl.value:
            self._show_table_error("Informe o Ts e selecione o EPL antes da condição.")
            return
        permitted = {option.value for option in available_options(self.epl.value, ts)}
        if value not in permitted:
            self._show_table_error("Esta condição não é permitida para o EPL e o Ts informados.")
            return
        self.option_group.value = value
        self._recalculate()

    def _on_mode_change(self, event: object | None = None) -> None:
        mode = self.mode_group.value or ConditionInputMode.CALCULATED.value
        if mode != TABLE17_MODE:
            self._table17_guide.visible = False
            self.epl.visible = True
            NewTestView._on_mode_change(self, event)
            self._set_table_view("simple")
            self.save_button.disabled = False
            self._refresh_result_views()
            return

        self.calculated_fields.visible = False
        self.direct_ts_fields.visible = True
        self.manual_condition_fields.visible = False
        self.option_panel.visible = False
        self.epl.visible = False
        self._table17_guide.visible = True
        self.manual_drying_fields.visible = False
        self._set_table_view("advanced")
        self._recalculate()

    def _recalculate(self, event: object | None = None) -> None:
        if self.mode_group.value != TABLE17_MODE:
            NewTestView._recalculate(self, event)
            self.save_button.disabled = False
            self._refresh_result_views()
            return

        self.error_banner.visible = False
        ts = _number(self.service_temperature.value)
        self.save_button.disabled = False
        if ts is None:
            self._condition = None
            self.ts_value.value = "Ts = —"
            self.option_help.value = "Informe o Ts para liberar a Tabela 17."
            self._refresh_result_views()
            self._refresh()
            return
        self.ts_value.value = f"Ts = {str(ts).replace('.', ',')} °C"
        if not self.epl.value:
            self._condition = None
            self.option_help.value = "Selecione um EPL diretamente na tabela."
            self._refresh_result_views()
            self._refresh()
            return
        try:
            permitted = {option.value for option in available_options(self.epl.value, ts)}
            if self.option_group.value not in permitted:
                self._condition = None
                self.option_help.value = "Selecione uma das condições liberadas na tabela."
            else:
                self._condition = resolve_condition(
                    self.epl.value,
                    ts,
                    self.option_group.value,
                )
                self._display_condition(self._condition)
                self.option_help.value = "Condição selecionada diretamente na Tabela 17."
        except (ClimateRuleError, InvalidOperation, ValueError) as error:
            self._condition = None
            self._show_error(str(error) or "Revise o Ts e a seleção da Tabela 17.")
        self._refresh_result_views()
        self._refresh()

    def _submit(self, event: object | None = None) -> None:
        required = [self.client, self.process_number, self.product, self.sample_quantity]
        mode = self.mode_group.value or ConditionInputMode.CALCULATED.value
        if mode == ConditionInputMode.CALCULATED.value:
            required.extend([self.epl, self.delta_t])
        elif mode == ConditionInputMode.DIRECT_TS.value:
            required.extend([self.epl, self.service_temperature])
        elif mode == ConditionInputMode.DIRECT_CONFIGURATION.value:
            required.extend(
                [
                    self.manual_chamber_temperature,
                    self.manual_chamber_humidity,
                    self.manual_chamber_duration,
                ]
            )
            if self.manual_drying_required.value:
                required.extend([self.manual_drying_temperature, self.manual_drying_duration])
        elif mode == TABLE17_MODE:
            required.append(self.service_temperature)

        missing = False
        for control in required:
            value = str(getattr(control, "value", "") or "").strip()
            control.error = None if value else "Campo obrigatório."
            missing = missing or not bool(value)
        if missing:
            self._show_error("Preencha todos os campos obrigatórios destacados.")
            self._refresh()
            return

        if self.mode_group.value != TABLE17_MODE:
            NewTestView._submit(self, event)
            return
        if self._condition is None or not self.epl.value or not self.option_group.value:
            self._show_error("Informe o Ts e selecione exatamente 1 EPL e 1 condição na Tabela 17.")
            self._refresh()
            return
        original = self.mode_group.value
        self.mode_group.value = ConditionInputMode.DIRECT_TS.value
        try:
            NewTestView._submit(self, event)
        finally:
            self.mode_group.value = original
