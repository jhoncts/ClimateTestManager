"""Formulário de cadastro com cálculo normativo em tempo real."""

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import flet as ft

from climatetest_manager.domain.climate_rules import (
    DEFAULT_TAMB_MAX_C,
    DURATION_POSITIVE_TOLERANCE_HOURS,
    HUMIDITY_PERCENT,
    HUMIDITY_TOLERANCE_PERCENT,
    NORMATIVE_RULE_VERSION,
    TEMPERATURE_TOLERANCE_K,
    ClimateCondition,
    ClimateRuleError,
    PhaseCondition,
    available_options,
    calculate_service_temperature,
    resolve_condition,
)
from climatetest_manager.domain.enums import EPL, ConditionInputMode, TestOption
from climatetest_manager.services.climate_tests import (
    ClimateTestDetails,
    CreateClimateTestCommand,
    UpdateClimateTestCommand,
)
from climatetest_manager.ui.components import ReasonSelector, section_heading
from climatetest_manager.ui.formatters import (
    format_decimal,
    format_duration_detail,
    normalize_decimal_input,
)
from climatetest_manager.ui.theme import AppColors


def _number_text(value: str) -> str:
    return value.strip().replace(",", ".")


@dataclass(frozen=True, slots=True)
class NewTestDraft:
    """Valores temporários mantidos enquanto o usuário consulta outra tela."""

    values: dict[str, object]


def _field(
    label: str,
    *,
    hint: str = "",
    multiline: bool = False,
    max_length: int | None = None,
) -> ft.TextField:
    return ft.TextField(
        label=label,
        hint_text=hint,
        max_length=max_length,
        counter="" if max_length is not None else None,
        multiline=multiline,
        min_lines=3 if multiline else None,
        max_lines=4 if multiline else None,
        border_radius=10,
        border_color=AppColors.DIVIDER,
        focused_border_color=AppColors.PRIMARY,
        bgcolor=AppColors.SURFACE,
    )


def _condition_item(
    icon: ft.IconData,
    title: str,
    value: ft.Text,
    detail: ft.Text | None = None,
    *,
    col: dict[str, int] | None = None,
) -> ft.Container:
    value.no_wrap = False
    text_controls: list[ft.Control] = [
        ft.Text(title, size=11, color=AppColors.TEXT_SECONDARY),
        value,
    ]
    if detail is not None:
        detail.no_wrap = False
        text_controls.append(detail)

    return ft.Container(
        col=col or {"xs": 12, "sm": 6},
        padding=ft.Padding.symmetric(horizontal=4, vertical=7),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=34,
                    height=34,
                    border_radius=10,
                    bgcolor=AppColors.SURFACE,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, size=18, color=AppColors.PRIMARY),
                ),
                ft.Column(
                    expand=True,
                    spacing=2,
                    controls=text_controls,
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
        on_save: Callable[[CreateClimateTestCommand | UpdateClimateTestCommand], None],
        details: ClimateTestDetails | None = None,
        draft: NewTestDraft | None = None,
    ) -> None:
        self._on_cancel = on_cancel
        self._on_save = on_save
        self._details = details
        self._condition: ClimateCondition | None = None
        self.mode_group = ft.RadioGroup(
            value=ConditionInputMode.CALCULATED.value,
            content=ft.Row(
                spacing=24,
                run_spacing=4,
                wrap=True,
                controls=[
                    ft.Radio(
                        value=ConditionInputMode.CALCULATED.value,
                        label="Calcular com Tamb + ΔT",
                    ),
                    ft.Radio(
                        value=ConditionInputMode.DIRECT_TS.value,
                        label="Usar Ts informado",
                    ),
                    ft.Radio(
                        value=ConditionInputMode.DIRECT_CONFIGURATION.value,
                        label="Personalizado",
                    ),
                ],
            ),
            on_change=self._on_mode_change,
        )

        self.client = _field(
            "Cliente *",
            hint="Nome ou razão social",
            max_length=120,
        )
        self.process_number = _field("Processo *", hint="Ex.: 26123.1", max_length=10)
        self.product = _field(
            "Produto *",
            hint="Ex.: Luminária Ex",
            max_length=160,
        )
        self.sample_quantity = _field(
            "Quantidade de amostras *",
            hint="Ex.: 2",
            max_length=2,
        )
        self.sample_quantity.value = "1"
        self.sample_quantity.keyboard_type = ft.KeyboardType.NUMBER
        self.sample_quantity.on_change = self._on_sample_quantity_change
        for field in (self.client, self.process_number, self.product):
            field.expand = True
        self.sample_quantity.expand = True
        self.epl = ft.Dropdown(
            label="EPL",
            hint_text="Selecione",
            options=[ft.DropdownOption(key=item.value, text=item.value) for item in EPL],
            border_radius=10,
            border_color=AppColors.DIVIDER,
            focused_border_color=AppColors.PRIMARY,
            bgcolor=AppColors.SURFACE,
            on_select=self._recalculate,
            expand=True,
        )
        self.tamb = _field(
            "Tamb máxima (°C)",
            hint="Em branco: adota +40",
            max_length=10,
        )
        self.delta_t = _field(
            "Delta T máximo (K) *",
            hint="Ex.: 35",
            max_length=10,
        )
        self.service_temperature = _field(
            "Ts informado (°C) *",
            hint="Ex.: 75",
            max_length=10,
        )
        self.ts_reference = _field(
            "Critério descrito no plano *",
            hint="Ex.: Ts > 70 °C — EPL Gb",
            max_length=100,
        )
        self.manual_chamber_temperature = _field(
            "Temperatura personalizada (°C) *",
            hint="Ex.: 90",
            max_length=10,
        )
        self.manual_chamber_duration = _field(
            "Permanência na câmara (h) *",
            hint="Ex.: 504",
            max_length=6,
        )
        self.manual_chamber_humidity = _field(
            "Umidade personalizada (% UR) *",
            hint="Ex.: 90",
            max_length=10,
        )
        self.manual_chamber_humidity.value = format_decimal(HUMIDITY_PERCENT)
        self.manual_drying_required = ft.Switch(
            label="O plano exige secagem",
            value=False,
            on_change=self._on_manual_drying_change,
        )
        self.manual_drying_temperature = _field(
            "Temperatura da secagem (0 a 100 °C) *",
            hint="Ex.: 95",
            max_length=10,
        )
        self.manual_drying_duration = _field(
            "Permanência na secagem (h) *",
            hint="Ex.: 336",
            max_length=6,
        )
        self.ts_reference.on_change = self._recalculate
        self.tamb.keyboard_type = ft.KeyboardType.NUMBER
        self.delta_t.keyboard_type = ft.KeyboardType.NUMBER
        for field in (
            self.tamb,
            self.delta_t,
            self.service_temperature,
            self.manual_chamber_temperature,
            self.manual_chamber_humidity,
            self.manual_chamber_duration,
            self.manual_drying_temperature,
            self.manual_drying_duration,
        ):
            field.keyboard_type = ft.KeyboardType.NUMBER
            field.expand = True
            field.on_change = self._on_condition_input_change
        # Não usamos InputFilter nativo nesses campos. No WebView2 ele pode
        # rejeitar o estado vazio e restaurar o último dígito digitado.
        # A normalização via on_change mantém somente números/vírgula e permite
        # apagar completamente o valor antes de digitar outro.
        self.tamb.expand = True
        self.delta_t.expand = True
        self.tamb.on_change = self._on_tamb_change
        self.delta_t.on_change = self._on_delta_t_change
        self.tamb_assumption = ft.Text(
            "Tamb não informada: será adotado +40 °C conforme a Tabela 1.",
            size=11,
            color=AppColors.TEXT_SECONDARY,
        )
        self.notes = _field(
            "Observações",
            hint="Informações adicionais",
            multiline=True,
            max_length=500,
        )
        self.change_reason_selector = ReasonSelector(
            (
                "Correção cadastral",
                "Revisão do plano de ensaio",
                "Solicitação do cliente",
                "Correção após conferência",
            ),
            other_hint="Resuma por que os dados estão sendo corrigidos",
        )

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
            "Informe EPL e Delta T para consultar as opções.",
            size=12,
            color=AppColors.TEXT_SECONDARY,
        )
        self.calculated_fields = ft.Container(
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.ResponsiveRow(
                        spacing=14,
                        run_spacing=12,
                        controls=[
                            ft.Container(
                                col={"xs": 12, "sm": 6},
                                content=self.tamb,
                            ),
                            ft.Container(
                                col={"xs": 12, "sm": 6},
                                content=self.delta_t,
                            ),
                        ],
                    ),
                    self.tamb_assumption,
                ],
            )
        )
        self.direct_ts_fields = ft.Container(
            visible=False,
            content=self.service_temperature,
        )
        self.manual_drying_fields = ft.ResponsiveRow(
            visible=False,
            spacing=14,
            run_spacing=12,
            controls=[
                ft.Container(
                    col={"xs": 12, "sm": 6},
                    content=self.manual_drying_temperature,
                ),
                ft.Container(
                    col={"xs": 12, "sm": 6},
                    content=self.manual_drying_duration,
                ),
            ],
        )
        self.manual_condition_fields = ft.Container(
            visible=False,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text(
                        "Informe a condição que será realmente aplicada. Temperatura e "
                        "umidade aceitam valores de 0 a 100; o tempo não possui limite "
                        "máximo e é informado em horas inteiras.",
                        size=11,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    ft.ResponsiveRow(
                        spacing=14,
                        run_spacing=12,
                        controls=[
                            ft.Container(
                                col={"xs": 12, "sm": 6, "lg": 4},
                                content=self.manual_chamber_temperature,
                            ),
                            ft.Container(
                                col={"xs": 12, "sm": 6, "lg": 4},
                                content=self.manual_chamber_humidity,
                            ),
                            ft.Container(
                                col={"xs": 12, "sm": 6, "lg": 4},
                                content=self.manual_chamber_duration,
                            ),
                        ],
                    ),
                    self.manual_drying_required,
                    self.manual_drying_fields,
                ],
            ),
        )
        self.option_panel = ft.Container(
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
        )

        value_style = {"size": 14, "weight": ft.FontWeight.BOLD, "color": AppColors.TEXT_PRIMARY}
        self.ts_value = ft.Text("—", **value_style)
        self.chamber_temperature = ft.Text("—", **value_style)
        self.chamber_humidity = ft.Text("—", **value_style)
        self.chamber_duration = ft.Text("—", **value_style)
        self.chamber_duration_detail = ft.Text("", size=11, color=AppColors.TEXT_SECONDARY)
        self.drying_temperature = ft.Text("—", **value_style)
        self.drying_duration = ft.Text("—", **value_style)
        self.drying_duration_detail = ft.Text("", size=11, color=AppColors.TEXT_SECONDARY)
        self.rule_reference = ft.Text("", size=11, color=AppColors.TEXT_SECONDARY)
        self.result_panel = self._build_result_panel()
        self.error_banner = ft.Container(visible=False)
        self.save_button = ft.Button(
            content="Salvar alterações" if details else "Salvar ensaio",
            icon=ft.Icons.SAVE,
            bgcolor=AppColors.PRIMARY,
            color=AppColors.WHITE,
            disabled=True,
            tooltip="Validar os dados e cadastrar o ensaio",
            on_click=self._submit,
        )
        self.root = self._build()
        self._refresh_targets = (
            self.calculated_fields,
            self.direct_ts_fields,
            self.manual_condition_fields,
            self.manual_drying_fields,
            self.option_panel,
            self.result_panel,
            self.error_banner,
            self.save_button,
            self.epl,
            self.tamb_assumption,
        )
        if details is not None:
            self._load_details(details)
        elif draft is not None:
            self.restore_draft(draft)

    def _build_result_panel(self) -> ft.Container:
        self.ts_value.color = AppColors.WHITE
        chamber_card = ft.Container(
            col={"xs": 12, "lg": 7},
            border_radius=14,
            bgcolor=AppColors.PRIMARY_LIGHT,
            border=ft.Border.all(1, AppColors.DIVIDER),
            padding=16,
            content=ft.Column(
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Row(
                        spacing=9,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=36,
                                height=36,
                                border_radius=11,
                                bgcolor=AppColors.PRIMARY,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(
                                    ft.Icons.WATER_DROP_OUTLINED,
                                    color=AppColors.WHITE,
                                    size=19,
                                ),
                            ),
                            ft.Column(
                                spacing=1,
                                controls=[
                                    ft.Text(
                                        "Câmara úmida",
                                        size=14,
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        "Condição principal do ensaio",
                                        size=10,
                                        color=AppColors.TEXT_SECONDARY,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.ResponsiveRow(
                        spacing=6,
                        run_spacing=4,
                        controls=[
                            _condition_item(
                                ft.Icons.THERMOSTAT,
                                "Temperatura",
                                self.chamber_temperature,
                            ),
                            _condition_item(
                                ft.Icons.WATER_DROP,
                                "Umidade",
                                self.chamber_humidity,
                            ),
                            _condition_item(
                                ft.Icons.SCHEDULE,
                                "Permanência",
                                self.chamber_duration,
                                self.chamber_duration_detail,
                                col={"xs": 12},
                            ),
                        ],
                    ),
                ],
            ),
        )
        drying_card = ft.Container(
            col={"xs": 12, "lg": 5},
            border_radius=14,
            bgcolor=AppColors.DRYING_LIGHT,
            border=ft.Border.all(1, AppColors.DIVIDER),
            padding=16,
            content=ft.Column(
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Row(
                        spacing=9,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=36,
                                height=36,
                                border_radius=11,
                                bgcolor=AppColors.DRYING,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(
                                    ft.Icons.AIR,
                                    color=AppColors.WHITE,
                                    size=19,
                                ),
                            ),
                            ft.Column(
                                spacing=1,
                                controls=[
                                    ft.Text(
                                        "Secagem",
                                        size=14,
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        "Etapa posterior, quando aplicável",
                                        size=10,
                                        color=AppColors.TEXT_SECONDARY,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.ResponsiveRow(
                        spacing=6,
                        run_spacing=4,
                        controls=[
                            _condition_item(
                                ft.Icons.THERMOSTAT,
                                "Temperatura",
                                self.drying_temperature,
                                col={"xs": 12, "sm": 6},
                            ),
                            _condition_item(
                                ft.Icons.AIR,
                                "Permanência",
                                self.drying_duration,
                                self.drying_duration_detail,
                                col={"xs": 12, "sm": 6},
                            ),
                        ],
                    ),
                ],
            ),
        )
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border_radius=16,
            border=ft.Border.all(1, AppColors.DIVIDER),
            padding=22,
            content=ft.Column(
                spacing=16,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.ResponsiveRow(
                        spacing=14,
                        run_spacing=12,
                        controls=[
                            ft.Container(
                                col={"xs": 12, "sm": 8},
                                content=ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text(
                                            "Prévia da condição",
                                            size=17,
                                            weight=ft.FontWeight.BOLD,
                                            color=AppColors.TEXT_PRIMARY,
                                        ),
                                        ft.Text(
                                            "Resultado calculado antes do salvamento.",
                                            size=11,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                ),
                            ),
                            ft.Container(
                                col={"xs": 12, "sm": 4},
                                alignment=ft.Alignment.CENTER_RIGHT,
                                content=ft.Container(
                                    border_radius=12,
                                    bgcolor=AppColors.PRIMARY,
                                    padding=ft.Padding.symmetric(
                                        horizontal=16,
                                        vertical=10,
                                    ),
                                    content=self.ts_value,
                                ),
                            ),
                        ],
                    ),
                    ft.ResponsiveRow(
                        spacing=10,
                        run_spacing=10,
                        controls=[chamber_card, drying_card],
                    ),
                    self.rule_reference,
                ],
            ),
        )

    def _identity_panel(self) -> ft.Container:
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border_radius=16,
            border=ft.Border.all(1, AppColors.DIVIDER),
            padding=22,
            content=ft.Column(
                spacing=16,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    section_heading(
                        "Identificação",
                        "Informe cliente, processo, produto e a quantidade física "
                        "de amostras deste ensaio.",
                    ),
                    ft.ResponsiveRow(
                        spacing=14,
                        run_spacing=12,
                        controls=[
                            ft.Container(
                                col={"xs": 12, "md": 8, "lg": 12},
                                content=self.client,
                            ),
                            ft.Container(
                                col={"xs": 12, "md": 4, "lg": 12},
                                content=self.process_number,
                            ),
                            ft.Container(
                                col={"xs": 12, "md": 8, "lg": 12},
                                content=self.product,
                            ),
                            ft.Container(
                                col={"xs": 12, "md": 4, "lg": 12},
                                content=self.sample_quantity,
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _notes_panel(self) -> ft.Container:
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border_radius=16,
            border=ft.Border.all(1, AppColors.DIVIDER),
            padding=22,
            content=ft.Column(
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Text(
                        "Informações complementares",
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    ft.ResponsiveRow(
                        controls=[
                            ft.Container(
                                col={"xs": 12},
                                content=self.notes,
                            )
                        ]
                    ),
                ],
            ),
        )

    def _thermal_panel(self) -> ft.Container:
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border_radius=16,
            border=ft.Border.all(1, AppColors.DIVIDER),
            padding=22,
            content=ft.Column(
                spacing=16,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    section_heading(
                        "Configuração térmica",
                        "Escolha a origem da condição. O sistema calcula e mostra "
                        "o resultado antes de permitir o salvamento.",
                    ),
                    ft.Container(
                        bgcolor=AppColors.PAGE_BACKGROUND,
                        border_radius=12,
                        border=ft.Border.all(1, AppColors.DIVIDER),
                        padding=14,
                        content=ft.Column(
                            spacing=7,
                            controls=[
                                ft.Text(
                                    "Como a condição será definida?",
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                self.mode_group,
                                ft.Text(
                                    "Use exatamente a origem registrada no plano "
                                    "ou informada pelo cliente.",
                                    size=11,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                    ),
                    self.epl,
                    self.calculated_fields,
                    self.direct_ts_fields,
                    self.manual_condition_fields,
                    self.option_panel,
                ],
            ),
        )

    def _build(self) -> ft.Column:
        left_column_controls: list[ft.Control] = [
            self._identity_panel(),
            self._notes_panel(),
        ]
        if self._details:
            left_column_controls.append(
                ft.Container(
                    bgcolor=AppColors.SURFACE,
                    border_radius=16,
                    border=ft.Border.all(1, AppColors.DIVIDER),
                    padding=22,
                    content=ft.ResponsiveRow(
                        controls=[
                            ft.Container(
                                col={"xs": 12},
                                content=self.change_reason_selector.control,
                            )
                        ]
                    ),
                )
            )
        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Column(
                    spacing=3,
                    controls=[
                        ft.Text(
                            "Editar ensaio" if self._details else "Novo ensaio",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                        ft.Text(
                            (
                                "Corrija os dados, confira os cálculos e informe o motivo "
                                "da alteração."
                                if self._details
                                else "Cadastre os dados e confira a condição calculada "
                                "antes de salvar."
                            ),
                            size=14,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
                *(
                    [
                        ft.Container(
                            bgcolor=AppColors.WARNING_LIGHT,
                            border_radius=12,
                            padding=14,
                            content=ft.Text(
                                "Alterações térmicas recalculam Ts, condição normativa e prazos "
                                "da etapa ativa. Os valores anteriores serão preservados no "
                                "registro de atividades.",
                                size=12,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                        )
                    ]
                    if self._details
                    else []
                ),
                self.error_banner,
                ft.ResponsiveRow(
                    spacing=16,
                    run_spacing=16,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Container(
                            col={"xs": 12, "lg": 5},
                            content=ft.Column(
                                spacing=16,
                                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                                controls=left_column_controls,
                            ),
                        ),
                        ft.Container(
                            col={"xs": 12, "lg": 7},
                            content=self._thermal_panel(),
                        ),
                    ],
                ),
                self.result_panel,
                ft.Container(
                    padding=ft.Padding.only(right=4),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        wrap=True,
                        run_spacing=10,
                        controls=[
                            ft.Button(
                                content="Cancelar",
                                tooltip="Descartar o rascunho e voltar ao Dashboard",
                                on_click=lambda _event: self._on_cancel(),
                            ),
                            self.save_button,
                        ],
                    ),
                ),
                ft.Container(height=8),
            ],
        )

    def _show_error(self, message: str) -> None:
        self.error_banner.content = ft.Row(
            spacing=10,
            controls=[
                ft.Icon(ft.Icons.ERROR_OUTLINE, color=AppColors.DANGER, size=20),
                ft.Text(
                    message,
                    expand=True,
                    size=13,
                    color=AppColors.TEXT_PRIMARY,
                ),
            ],
        )
        self.error_banner.bgcolor = AppColors.DANGER_LIGHT
        self.error_banner.border_radius = 12
        self.error_banner.padding = 14
        self.error_banner.visible = True

    def _load_details(self, details: ClimateTestDetails) -> None:
        mode = details.input_mode
        if mode in {
            ConditionInputMode.PLAN_DEFINED.value,
            ConditionInputMode.PLAN_CRITERION.value,
        }:
            mode = ConditionInputMode.DIRECT_CONFIGURATION.value
        self.mode_group.value = mode
        self.client.value = details.client
        self.process_number.value = details.process_number
        self.product.value = details.product
        self.sample_quantity.value = str(details.sample_quantity)
        self.epl.value = details.epl or None
        self.tamb.value = format_decimal(details.tamb_max_c)
        self.delta_t.value = format_decimal(details.delta_t_max_k)
        self.service_temperature.value = (
            format_decimal(details.service_temperature_c)
            if mode == ConditionInputMode.DIRECT_TS.value
            else ""
        )
        self.ts_reference.value = details.ts_reference or ""
        self.manual_chamber_temperature.value = format_decimal(details.chamber_temperature_c)
        self.manual_chamber_humidity.value = format_decimal(details.chamber_humidity_percent)
        self.manual_chamber_duration.value = str(details.chamber_duration_hours)
        self.manual_drying_required.value = details.drying_required
        self.manual_drying_temperature.value = (
            format_decimal(details.drying_temperature_c)
            if details.drying_temperature_c is not None
            else ""
        )
        self.manual_drying_duration.value = (
            str(details.drying_duration_hours) if details.drying_duration_hours is not None else ""
        )
        self.option_group.value = (
            details.selected_option if details.selected_option in {"A", "B"} else None
        )
        self.notes.value = details.notes or ""
        self._on_mode_change()

    def snapshot_draft(self) -> NewTestDraft:
        """Captura o formulário sem gravar um ensaio incompleto no banco."""

        fields = {
            "client": self.client.value,
            "process_number": self.process_number.value,
            "product": self.product.value,
            "sample_quantity": self.sample_quantity.value,
            "epl": self.epl.value,
            "tamb": self.tamb.value,
            "delta_t": self.delta_t.value,
            "service_temperature": self.service_temperature.value,
            "ts_reference": self.ts_reference.value,
            "manual_chamber_temperature": self.manual_chamber_temperature.value,
            "manual_chamber_humidity": self.manual_chamber_humidity.value,
            "manual_chamber_duration": self.manual_chamber_duration.value,
            "manual_drying_required": bool(self.manual_drying_required.value),
            "manual_drying_temperature": self.manual_drying_temperature.value,
            "manual_drying_duration": self.manual_drying_duration.value,
            "notes": self.notes.value,
            "mode": self.mode_group.value,
            "option": self.option_group.value,
        }
        return NewTestDraft(fields)

    def restore_draft(self, draft: NewTestDraft) -> None:
        """Restaura os valores após a navegação para Agenda ou outra tela."""

        values = draft.values
        for name in (
            "client",
            "process_number",
            "product",
            "sample_quantity",
            "tamb",
            "delta_t",
            "service_temperature",
            "ts_reference",
            "manual_chamber_temperature",
            "manual_chamber_humidity",
            "manual_chamber_duration",
            "manual_drying_temperature",
            "manual_drying_duration",
            "notes",
        ):
            control = getattr(self, name)
            value = values.get(name)
            if isinstance(value, str):
                control.value = value
        epl = values.get("epl")
        self.epl.value = epl if isinstance(epl, str) and epl else None
        mode = values.get("mode")
        if isinstance(mode, str):
            self.mode_group.value = mode
        option = values.get("option")
        self.option_group.value = option if isinstance(option, str) else None
        self.manual_drying_required.value = bool(values.get("manual_drying_required", False))
        self._on_mode_change()

    def _refresh(self) -> None:
        """Atualiza somente a condição, preservando a posição real da rolagem."""

        try:
            page = self.root.page
        except RuntimeError:
            return
        page.update(*self._refresh_targets)

    def _on_tamb_change(self, _event: object | None = None) -> None:
        self.tamb.value = normalize_decimal_input(self.tamb.value, allow_negative=True)
        self._recalculate()

    def _on_delta_t_change(self, _event: object | None = None) -> None:
        self.delta_t.value = normalize_decimal_input(self.delta_t.value)
        self._recalculate()

    def _on_sample_quantity_change(self, _event: object | None = None) -> None:
        digits = "".join(
            character for character in self.sample_quantity.value if character.isdigit()
        )
        normalized = digits.lstrip("0")[:2]
        if normalized == self.sample_quantity.value:
            return
        self.sample_quantity.value = normalized
        self.sample_quantity.selection = ft.TextSelection(
            base_offset=len(normalized),
            extent_offset=len(normalized),
        )
        with suppress(RuntimeError):
            self.sample_quantity.update()

    def _on_mode_change(self, _event: object | None = None) -> None:
        mode = self.mode_group.value or ConditionInputMode.CALCULATED.value
        self.calculated_fields.visible = mode == ConditionInputMode.CALCULATED.value
        self.direct_ts_fields.visible = mode == ConditionInputMode.DIRECT_TS.value
        manual_mode = mode == ConditionInputMode.DIRECT_CONFIGURATION.value
        self.manual_condition_fields.visible = manual_mode
        self.option_panel.visible = mode in {
            ConditionInputMode.CALCULATED.value,
            ConditionInputMode.DIRECT_TS.value,
        }
        if mode == ConditionInputMode.DIRECT_CONFIGURATION.value:
            self.epl.label = "EPL (opcional)"
        else:
            self.epl.label = "EPL *"
        self.manual_drying_fields.visible = bool(self.manual_drying_required.value)
        self._recalculate()

    def _on_condition_input_change(self, _event: object | None = None) -> None:
        for field in (
            self.service_temperature,
            self.manual_chamber_temperature,
            self.manual_chamber_humidity,
            self.manual_drying_temperature,
        ):
            field.value = normalize_decimal_input(field.value)
        for field in (self.manual_chamber_duration, self.manual_drying_duration):
            field.value = "".join(character for character in field.value if character.isdigit())
        self._recalculate()

    def _on_manual_drying_change(self, _event: object | None = None) -> None:
        self.manual_drying_fields.visible = bool(self.manual_drying_required.value)
        self._recalculate()

    def _clear_condition(self, help_text: str) -> None:
        self._condition = None
        self.save_button.disabled = True
        self.ts_value.value = "Ts = —"
        self.option_help.value = help_text

    def _manual_condition(self) -> ClimateCondition:
        chamber_temperature = Decimal(_number_text(self.manual_chamber_temperature.value))
        chamber_humidity = Decimal(_number_text(self.manual_chamber_humidity.value))
        if not Decimal("0") <= chamber_temperature <= Decimal("100"):
            raise ValueError("Temperatura da câmara deve estar entre 0 e 100 °C.")
        if not Decimal("0") <= chamber_humidity <= Decimal("100"):
            raise ValueError("Umidade da câmara deve estar entre 0 e 100%.")
        chamber_duration = int(self.manual_chamber_duration.value)
        if chamber_duration < 1:
            raise ValueError("Permanência da câmara deve ser maior que zero.")
        drying: PhaseCondition | None = None
        if self.manual_drying_required.value:
            drying_temperature = Decimal(_number_text(self.manual_drying_temperature.value))
            if not Decimal("0") <= drying_temperature <= Decimal("100"):
                raise ValueError("Temperatura da secagem deve estar entre 0 e 100 °C.")
            drying_duration = int(self.manual_drying_duration.value)
            if drying_duration < 1:
                raise ValueError("Permanência da secagem deve ser maior que zero.")
            drying = PhaseCondition(
                temperature_c=drying_temperature,
                duration_hours=drying_duration,
                temperature_tolerance_k=TEMPERATURE_TOLERANCE_K,
                duration_positive_tolerance_hours=DURATION_POSITIVE_TOLERANCE_HOURS,
            )
        return ClimateCondition(
            epl=EPL(self.epl.value) if self.epl.value else None,
            service_temperature_c=Decimal("0"),
            option=None,
            chamber=PhaseCondition(
                temperature_c=chamber_temperature,
                duration_hours=chamber_duration,
                temperature_tolerance_k=TEMPERATURE_TOLERANCE_K,
                duration_positive_tolerance_hours=DURATION_POSITIVE_TOLERANCE_HOURS,
                humidity_percent=chamber_humidity,
                humidity_tolerance_percent=HUMIDITY_TOLERANCE_PERCENT,
            ),
            drying=drying,
            rule_id="DIRECT-CONFIGURATION",
            normative_rule_version=f"{NORMATIVE_RULE_VERSION}+CONFIGURACAO-DIRETA",
        )

    def _recalculate(self, _event: object | None = None) -> None:
        self.error_banner.visible = False
        mode = self.mode_group.value or ConditionInputMode.CALCULATED.value
        self.option_b.disabled = False
        epl_required = mode != ConditionInputMode.DIRECT_CONFIGURATION.value
        if epl_required and not self.epl.value:
            self._clear_condition("Informe o EPL para continuar.")
            self._refresh()
            return

        try:
            if mode == ConditionInputMode.CALCULATED.value:
                tamb_was_defaulted = not self.tamb.value.strip()
                self.tamb_assumption.visible = tamb_was_defaulted
                if not self.delta_t.value.strip():
                    self._clear_condition("Informe o Delta T para calcular Ts.")
                    self._refresh()
                    return
                effective_tamb = (
                    format_decimal(DEFAULT_TAMB_MAX_C)
                    if tamb_was_defaulted
                    else _number_text(self.tamb.value)
                )
                ts = calculate_service_temperature(
                    effective_tamb,
                    _number_text(self.delta_t.value),
                )
                options = available_options(self.epl.value, ts)
                option_values = {option.value for option in options}
                self.option_b.disabled = TestOption.B.value not in option_values
                if self.option_group.value not in option_values:
                    self.option_group.value = TestOption.A.value
                self.option_help.value = (
                    "Somente a opção A é aplicável para esta combinação."
                    if len(options) == 1
                    else "As opções A e B são permitidas. Confirme sua escolha."
                )
                self._condition = resolve_condition(
                    self.epl.value,
                    ts,
                    self.option_group.value,
                )
            elif mode == ConditionInputMode.DIRECT_TS.value:
                self.tamb_assumption.visible = False
                if not self.service_temperature.value.strip():
                    self._clear_condition("Informe o Ts indicado pelo cliente ou plano.")
                    self._refresh()
                    return
                ts = Decimal(_number_text(self.service_temperature.value))
                options = available_options(self.epl.value, ts)
                option_values = {option.value for option in options}
                self.option_b.disabled = TestOption.B.value not in option_values
                if self.option_group.value not in option_values:
                    self.option_group.value = TestOption.A.value
                self.option_help.value = (
                    "Somente a opção A é aplicável para este Ts."
                    if len(options) == 1
                    else "As opções A e B são permitidas. Confirme sua escolha."
                )
                self._condition = resolve_condition(
                    self.epl.value,
                    ts,
                    self.option_group.value,
                )
            else:
                self.tamb_assumption.visible = False
                required_manual = (
                    self.manual_chamber_temperature.value.strip()
                    and self.manual_chamber_humidity.value.strip()
                    and self.manual_chamber_duration.value.strip()
                )
                if self.manual_drying_required.value:
                    required_manual = bool(
                        required_manual
                        and self.manual_drying_temperature.value.strip()
                        and self.manual_drying_duration.value.strip()
                    )
                if not required_manual:
                    self._clear_condition("Informe a condição personalizada que será aplicada.")
                    self._refresh()
                    return
                self._condition = self._manual_condition()
            self._display_condition(self._condition)
            if mode == ConditionInputMode.DIRECT_CONFIGURATION.value:
                self.ts_value.value = "Ts não informado"
            self.save_button.disabled = False
        except (ClimateRuleError, InvalidOperation, ValueError) as error:
            self._clear_condition(str(error) or "Revise os valores informados.")
            self.option_help.value = str(error)
        self._refresh()

    def _display_condition(self, condition: ClimateCondition) -> None:
        chamber = condition.chamber
        self.ts_value.value = f"Ts = {format_decimal(condition.service_temperature_c)} °C"
        self.chamber_temperature.value = (
            f"{format_decimal(chamber.temperature_c)} ± "
            f"{format_decimal(chamber.temperature_tolerance_k)} °C"
        )
        self.chamber_humidity.value = (
            f"{format_decimal(chamber.humidity_percent or Decimal('0'))} ± "
            f"{format_decimal(chamber.humidity_tolerance_percent or Decimal('0'))} % UR"
        )
        self.chamber_duration.value = (
            f"{chamber.duration_hours} h (+{chamber.duration_positive_tolerance_hours} h)"
        )
        self.chamber_duration_detail.value = format_duration_detail(
            chamber.duration_hours, chamber.duration_positive_tolerance_hours
        )
        if condition.drying:
            drying = condition.drying
            self.drying_temperature.value = (
                f"{format_decimal(drying.temperature_c)} ± "
                f"{format_decimal(drying.temperature_tolerance_k)} °C"
            )
            self.drying_duration.value = (
                f"{drying.duration_hours} h (+{drying.duration_positive_tolerance_hours} h)"
            )
            self.drying_duration_detail.value = format_duration_detail(
                drying.duration_hours, drying.duration_positive_tolerance_hours
            )
        else:
            self.drying_temperature.value = "Não requerida"
            self.drying_duration.value = "—"
            self.drying_duration_detail.value = ""
        self.rule_reference.value = f"Condição registrada • {condition.normative_rule_version}" + (
            f" • Opção {condition.option.value}" if condition.option is not None else ""
        )

    def _submit(self, _event: object | None = None) -> None:
        required_fields = [
            (self.client, "Cliente"),
            (self.process_number, "Processo"),
            (self.product, "Produto"),
            (self.sample_quantity, "Quantidade de amostras"),
        ]
        missing = False
        for field, label in required_fields:
            field.error = None if field.value.strip() else f"Preencha {label}."
            missing = missing or not bool(field.value.strip())

        if missing or self._condition is None:
            self._show_error("Revise os campos obrigatórios e os dados térmicos.")
            self._refresh()
            return

        if not self.sample_quantity.value.isdigit() or int(self.sample_quantity.value) < 1:
            self.sample_quantity.error = "Informe um número inteiro maior que zero."
            self._show_error("Revise a quantidade de amostras.")
            self._refresh()
            return

        common_values = {
            "client": self.client.value,
            "process_number": self.process_number.value,
            "product": self.product.value,
            "epl": self.epl.value or "",
            "tamb_max_c": self.tamb.value,
            "delta_t_max_k": self.delta_t.value,
            "selected_option": (
                self.option_group.value or ""
                if self.mode_group.value
                in {
                    ConditionInputMode.CALCULATED.value,
                    ConditionInputMode.DIRECT_TS.value,
                }
                else ""
            ),
            "sample_quantity": self.sample_quantity.value,
            "notes": self.notes.value,
            "input_mode": self.mode_group.value or ConditionInputMode.CALCULATED.value,
            "service_temperature_c": self.service_temperature.value,
            "ts_reference": "",
            "manual_chamber_temperature_c": self.manual_chamber_temperature.value,
            "manual_chamber_humidity_percent": self.manual_chamber_humidity.value,
            "manual_chamber_duration_hours": self.manual_chamber_duration.value,
            "manual_drying_required": bool(self.manual_drying_required.value),
            "manual_drying_temperature_c": self.manual_drying_temperature.value,
            "manual_drying_duration_hours": self.manual_drying_duration.value,
        }
        if self._details is not None:
            if not self.change_reason_selector.validate(message="Selecione o motivo da alteração."):
                self._show_error("O motivo é obrigatório para preservar a rastreabilidade.")
                self._refresh()
                return
            command: CreateClimateTestCommand | UpdateClimateTestCommand = UpdateClimateTestCommand(
                **common_values,
                reason=self.change_reason_selector.value(),
            )
        else:
            command = CreateClimateTestCommand(**common_values)
        try:
            self._on_save(command)
        except ValueError as error:
            self._show_error(str(error))
            self._refresh()


def build_new_test_view(
    *,
    on_cancel: Callable[[], None],
    on_save: Callable[[CreateClimateTestCommand], None],
    draft: NewTestDraft | None = None,
) -> ft.Column:
    """Cria uma nova instância limpa do formulário."""

    return NewTestView(on_cancel=on_cancel, on_save=on_save, draft=draft).root


def build_edit_test_view(
    details: ClimateTestDetails,
    *,
    on_cancel: Callable[[], None],
    on_save: Callable[[UpdateClimateTestCommand], None],
) -> ft.Column:
    """Cria o formulário preenchido para correção auditável de um ensaio."""

    return NewTestView(
        on_cancel=on_cancel,
        on_save=on_save,  # type: ignore[arg-type]
        details=details,
    ).root
