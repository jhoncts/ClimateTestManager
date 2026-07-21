"""Formulário de cadastro com cálculo normativo em tempo real."""

from collections.abc import Callable
from decimal import Decimal

import flet as ft

from climatetest_manager.domain.climate_rules import (
    ClimateCondition,
    ClimateRuleError,
    available_options,
    calculate_service_temperature,
    resolve_condition,
)
from climatetest_manager.domain.enums import EPL, TestOption
from climatetest_manager.services.climate_tests import CreateClimateTestCommand
from climatetest_manager.ui.theme import AppColors


def _format_number(value: Decimal) -> str:
    return format(value, "f").rstrip("0").rstrip(".") or "0"


def _number_text(value: str) -> str:
    return value.strip().replace(",", ".")


def _field(label: str, *, hint: str = "", multiline: bool = False) -> ft.TextField:
    return ft.TextField(
        label=label,
        hint_text=hint,
        multiline=multiline,
        min_lines=3 if multiline else None,
        max_lines=4 if multiline else None,
        border_radius=10,
        border_color=AppColors.DIVIDER,
        focused_border_color=AppColors.PRIMARY,
        bgcolor=AppColors.SURFACE,
    )


def _condition_item(icon: ft.IconData, title: str, value: ft.Text) -> ft.Container:
    return ft.Container(
        expand=True,
        border_radius=12,
        bgcolor=AppColors.PAGE_BACKGROUND,
        padding=14,
        content=ft.Row(
            spacing=10,
            controls=[
                ft.Icon(icon, size=20, color=AppColors.PRIMARY),
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(title, size=11, color=AppColors.TEXT_SECONDARY),
                        value,
                    ],
                ),
            ],
        ),
    )


class NewTestView:
    """Mantém os controles e o estado temporário do formulário."""

    def __init__(
        self,
        *,
        on_cancel: Callable[[], None],
        on_save: Callable[[CreateClimateTestCommand], None],
    ) -> None:
        self._on_cancel = on_cancel
        self._on_save = on_save
        self._condition: ClimateCondition | None = None

        self.client = _field("Cliente *", hint="Nome ou razão social")
        self.process_number = _field("Processo *", hint="Ex.: 26000.001234/2026-10")
        self.product = _field("Produto *", hint="Ex.: Luminária Ex")
        self.ex_marking = _field("Marcação Ex *", hint="Ex.: Ex db IIC T6 Gb")
        for field in (self.client, self.process_number, self.product, self.ex_marking):
            field.expand = True
        self.epl = ft.Dropdown(
            label="EPL *",
            hint_text="Selecione",
            options=[ft.DropdownOption(key=item.value, text=item.value) for item in EPL],
            border_radius=10,
            border_color=AppColors.DIVIDER,
            focused_border_color=AppColors.PRIMARY,
            bgcolor=AppColors.SURFACE,
            on_select=self._recalculate,
            expand=True,
        )
        self.tamb = _field("Tamb máxima (°C) *", hint="Ex.: 40")
        self.delta_t = _field("Delta T máximo (K) *", hint="Ex.: 35")
        self.tamb.keyboard_type = ft.KeyboardType.NUMBER
        self.delta_t.keyboard_type = ft.KeyboardType.NUMBER
        self.tamb.expand = True
        self.delta_t.expand = True
        self.tamb.on_change = self._recalculate
        self.delta_t.on_change = self._recalculate
        self.notes = _field("Observações", hint="Informações adicionais", multiline=True)

        self.option_b = ft.Radio(value="B", label="Opção B", disabled=True)
        self.option_group = ft.RadioGroup(
            content=ft.Row(
                spacing=28,
                controls=[
                    ft.Radio(value="A", label="Opção A"),
                    self.option_b,
                ],
            ),
            on_change=self._recalculate,
        )
        self.option_help = ft.Text(
            "Informe EPL, Tamb e Delta T para consultar as opções.",
            size=12,
            color=AppColors.TEXT_SECONDARY,
        )

        value_style = {"size": 14, "weight": ft.FontWeight.BOLD, "color": AppColors.TEXT_PRIMARY}
        self.ts_value = ft.Text("—", **value_style)
        self.chamber_temperature = ft.Text("—", **value_style)
        self.chamber_humidity = ft.Text("—", **value_style)
        self.chamber_duration = ft.Text("—", **value_style)
        self.drying_temperature = ft.Text("—", **value_style)
        self.drying_duration = ft.Text("—", **value_style)
        self.rule_reference = ft.Text("", size=11, color=AppColors.TEXT_SECONDARY)
        self.result_panel = self._build_result_panel()
        self.error_banner = ft.Container(visible=False)
        self.save_button = ft.Button(
            content="Salvar ensaio",
            icon=ft.Icons.SAVE,
            bgcolor=AppColors.PRIMARY,
            color=AppColors.WHITE,
            disabled=True,
            on_click=self._submit,
        )
        self.root = self._build()

    def _build_result_panel(self) -> ft.Container:
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border_radius=16,
            padding=22,
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                "Condição calculada",
                                size=17,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            self.ts_value,
                        ],
                    ),
                    ft.Text(
                        "Câmara úmida",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.PRIMARY,
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            _condition_item(
                                ft.Icons.THERMOSTAT, "Temperatura", self.chamber_temperature
                            ),
                            _condition_item(ft.Icons.WATER_DROP, "Umidade", self.chamber_humidity),
                            _condition_item(
                                ft.Icons.SCHEDULE, "Permanência", self.chamber_duration
                            ),
                        ],
                    ),
                    ft.Divider(height=1, color=AppColors.DIVIDER),
                    ft.Text(
                        "Secagem",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.DRYING,
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            _condition_item(
                                ft.Icons.THERMOSTAT, "Temperatura", self.drying_temperature
                            ),
                            _condition_item(ft.Icons.AIR, "Permanência", self.drying_duration),
                        ],
                    ),
                    self.rule_reference,
                ],
            ),
        )

    def _build(self) -> ft.Column:
        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            controls=[
                ft.Column(
                    spacing=3,
                    controls=[
                        ft.Text(
                            "Novo ensaio",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                        ft.Text(
                            "Cadastre os dados e confira a condição calculada antes de salvar.",
                            size=14,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
                self.error_banner,
                ft.Container(
                    bgcolor=AppColors.SURFACE,
                    border_radius=16,
                    padding=22,
                    content=ft.Column(
                        spacing=16,
                        controls=[
                            ft.Text(
                                "Identificação",
                                size=17,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            ft.Row(spacing=14, controls=[self.client, self.process_number]),
                            ft.Row(spacing=14, controls=[self.product, self.ex_marking]),
                            ft.Text(
                                "Dados térmicos",
                                size=17,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            ft.Row(spacing=14, controls=[self.epl, self.tamb, self.delta_t]),
                            ft.Container(
                                bgcolor=AppColors.INFO_LIGHT,
                                border_radius=12,
                                padding=14,
                                content=ft.Column(
                                    spacing=4,
                                    controls=[
                                        ft.Text(
                                            "Alternativa da Tabela 17",
                                            size=13,
                                            weight=ft.FontWeight.BOLD,
                                            color=AppColors.TEXT_PRIMARY,
                                        ),
                                        self.option_group,
                                        self.option_help,
                                    ],
                                ),
                            ),
                        ],
                    ),
                ),
                self.result_panel,
                ft.Container(
                    bgcolor=AppColors.SURFACE,
                    border_radius=16,
                    padding=22,
                    content=self.notes,
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    controls=[
                        ft.Button(content="Cancelar", on_click=lambda _event: self._on_cancel()),
                        self.save_button,
                    ],
                ),
                ft.Container(height=8),
            ],
        )

    def _show_error(self, message: str) -> None:
        self.error_banner.content = ft.Row(
            spacing=10,
            controls=[
                ft.Icon(ft.Icons.ERROR_OUTLINE, color=AppColors.DANGER, size=20),
                ft.Text(message, size=13, color=AppColors.TEXT_PRIMARY),
            ],
        )
        self.error_banner.bgcolor = AppColors.DANGER_LIGHT
        self.error_banner.border_radius = 12
        self.error_banner.padding = 14
        self.error_banner.visible = True

    def _refresh(self) -> None:
        """Atualiza a tela quando o controle já pertence a uma página Flet."""

        try:
            _page = self.root.page
        except RuntimeError:
            return
        self.root.update()

    def _recalculate(self, _event: object | None = None) -> None:
        self.error_banner.visible = False
        if not self.epl.value or not self.tamb.value.strip() or not self.delta_t.value.strip():
            self._condition = None
            self.save_button.disabled = True
            self.ts_value.value = "Ts = —"
            self.option_help.value = "Informe EPL, Tamb e Delta T para consultar as opções."
            self._refresh()
            return

        try:
            ts = calculate_service_temperature(
                _number_text(self.tamb.value), _number_text(self.delta_t.value)
            )
            options = available_options(self.epl.value, ts)
            option_values = {option.value for option in options}
            self.option_b.disabled = TestOption.B.value not in option_values
            if self.option_group.value not in option_values:
                self.option_group.value = TestOption.A.value

            if len(options) == 1:
                self.option_help.value = "Somente a opção A é aplicável para esta combinação."
            else:
                self.option_help.value = "As opções A e B são permitidas. Confirme sua escolha."

            self._condition = resolve_condition(self.epl.value, ts, self.option_group.value)
            self._display_condition(self._condition)
            self.save_button.disabled = False
        except ClimateRuleError as error:
            self._condition = None
            self.save_button.disabled = True
            self.ts_value.value = "Ts = —"
            self.option_help.value = str(error)
        self._refresh()

    def _display_condition(self, condition: ClimateCondition) -> None:
        chamber = condition.chamber
        self.ts_value.value = f"Ts = {_format_number(condition.service_temperature_c)} °C"
        self.chamber_temperature.value = (
            f"{_format_number(chamber.temperature_c)} ± "
            f"{_format_number(chamber.temperature_tolerance_k)} °C"
        )
        self.chamber_humidity.value = (
            f"{_format_number(chamber.humidity_percent or Decimal('0'))} ± "
            f"{_format_number(chamber.humidity_tolerance_percent or Decimal('0'))} % UR"
        )
        self.chamber_duration.value = (
            f"{chamber.duration_hours} h (+{chamber.duration_positive_tolerance_hours} h)"
        )
        if condition.drying:
            drying = condition.drying
            self.drying_temperature.value = (
                f"{_format_number(drying.temperature_c)} ± "
                f"{_format_number(drying.temperature_tolerance_k)} °C"
            )
            self.drying_duration.value = (
                f"{drying.duration_hours} h (+{drying.duration_positive_tolerance_hours} h)"
            )
        else:
            self.drying_temperature.value = "Não requerida"
            self.drying_duration.value = "—"
        self.rule_reference.value = (
            f"Regra {condition.rule_id} • {condition.normative_rule_version} • "
            f"Opção {condition.option.value}"
        )

    def _submit(self, _event: object | None = None) -> None:
        required_fields = [
            (self.client, "Cliente"),
            (self.process_number, "Processo"),
            (self.product, "Produto"),
            (self.ex_marking, "Marcação Ex"),
        ]
        missing = False
        for field, label in required_fields:
            field.error = None if field.value.strip() else f"Preencha {label}."
            missing = missing or not bool(field.value.strip())

        if missing or self._condition is None:
            self._show_error("Revise os campos obrigatórios e os dados térmicos.")
            self._refresh()
            return

        command = CreateClimateTestCommand(
            client=self.client.value,
            process_number=self.process_number.value,
            product=self.product.value,
            ex_marking=self.ex_marking.value,
            epl=self.epl.value or "",
            tamb_max_c=self.tamb.value,
            delta_t_max_k=self.delta_t.value,
            selected_option=self.option_group.value or "",
            notes=self.notes.value,
        )
        try:
            self._on_save(command)
        except ValueError as error:
            self._show_error(str(error))
            self._refresh()


def build_new_test_view(
    *,
    on_cancel: Callable[[], None],
    on_save: Callable[[CreateClimateTestCommand], None],
) -> ft.Column:
    """Cria uma nova instância limpa do formulário."""

    return NewTestView(on_cancel=on_cancel, on_save=on_save).root
