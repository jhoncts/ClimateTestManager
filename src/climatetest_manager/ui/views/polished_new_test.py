"""Versão de produção do formulário de ensaio com hierarquia visual mais compacta."""

from __future__ import annotations

import flet as ft

from climatetest_manager.services.climate_tests import ClimateTestDetails
from climatetest_manager.ui.components import section_heading
from climatetest_manager.ui.components.table17 import build_table17_preview
from climatetest_manager.ui.interaction import glass_surface
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.ui.views.new_test import NewTestDraft, NewTestView


def _compact_value(
    icon: ft.IconData,
    label: str,
    value: ft.Text,
    detail: ft.Text | None = None,
    *,
    col: dict[str, int] | None = None,
) -> ft.Container:
    value.no_wrap = False
    return ft.Container(
        col=col or {"xs": 12, "sm": 4},
        border_radius=12,
        bgcolor=AppColors.SURFACE,
        border=ft.Border.all(1, AppColors.DIVIDER),
        padding=11,
        content=ft.Column(
            spacing=4,
            controls=[
                ft.Row(
                    spacing=7,
                    controls=[
                        ft.Icon(icon, size=17, color=AppColors.PRIMARY),
                        ft.Text(label, size=10, color=AppColors.TEXT_SECONDARY),
                    ],
                ),
                value,
                *([detail] if detail is not None else []),
            ],
        ),
    )


class PolishedNewTestView(NewTestView):
    """Mantém toda a regra existente e troca somente composição/apresentação."""

    def __init__(
        self,
        *,
        on_cancel,
        on_save,
        details: ClimateTestDetails | None = None,
        draft: NewTestDraft | None = None,
    ) -> None:
        self.table17_host = ft.Container()
        super().__init__(
            on_cancel=on_cancel,
            on_save=on_save,
            details=details,
            draft=draft,
        )
        self._refresh_targets = (*self._refresh_targets, self.table17_host)

    def _identity_panel(self) -> ft.Container:
        return glass_surface(
            ft.Column(
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    section_heading(
                        "Identificação do ensaio",
                        "Dados essenciais do processo e das amostras.",
                    ),
                    ft.ResponsiveRow(
                        spacing=12,
                        run_spacing=10,
                        controls=[
                            ft.Container(col={"xs": 12, "md": 8}, content=self.client),
                            ft.Container(col={"xs": 12, "md": 4}, content=self.process_number),
                            ft.Container(col={"xs": 12, "md": 9}, content=self.product),
                            ft.Container(col={"xs": 12, "md": 3}, content=self.sample_quantity),
                        ],
                    ),
                ],
            ),
            padding=18,
        )

    def _thermal_panel(self) -> ft.Container:
        return glass_surface(
            ft.Column(
                spacing=13,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    section_heading(
                        "Condição térmica",
                        "Escolha a origem dos dados; a condição aplicável aparece imediatamente.",
                    ),
                    ft.Container(
                        border_radius=12,
                        bgcolor=AppColors.PAGE_BACKGROUND,
                        border=ft.Border.all(1, AppColors.DIVIDER),
                        padding=12,
                        content=ft.Column(
                            spacing=5,
                            controls=[
                                ft.Text(
                                    "Origem da condição",
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                                self.mode_group,
                            ],
                        ),
                    ),
                    ft.ResponsiveRow(
                        spacing=12,
                        run_spacing=10,
                        controls=[
                            ft.Container(col={"xs": 12, "sm": 4}, content=self.epl),
                            ft.Container(
                                col={"xs": 12, "sm": 8},
                                content=ft.Column(
                                    spacing=6,
                                    controls=[
                                        self.calculated_fields,
                                        self.direct_ts_fields,
                                    ],
                                ),
                            ),
                        ],
                    ),
                    self.manual_condition_fields,
                    self.option_panel,
                ],
            ),
            padding=18,
            accent=True,
        )

    def _notes_panel(self) -> ft.Container:
        return glass_surface(
            ft.Column(
                spacing=9,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Text(
                        "Observações",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    self.notes,
                ],
            ),
            padding=16,
        )

    def _build_result_panel(self) -> ft.Container:
        self.ts_value.color = AppColors.WHITE
        condition_cards = ft.ResponsiveRow(
            spacing=10,
            run_spacing=10,
            controls=[
                _compact_value(
                    ft.Icons.THERMOSTAT,
                    "Temperatura da câmara",
                    self.chamber_temperature,
                ),
                _compact_value(
                    ft.Icons.WATER_DROP_OUTLINED,
                    "Umidade",
                    self.chamber_humidity,
                ),
                _compact_value(
                    ft.Icons.SCHEDULE,
                    "Permanência",
                    self.chamber_duration,
                    self.chamber_duration_detail,
                ),
            ],
        )
        drying_cards = ft.ResponsiveRow(
            spacing=10,
            run_spacing=10,
            controls=[
                _compact_value(
                    ft.Icons.THERMOSTAT,
                    "Temperatura de secagem",
                    self.drying_temperature,
                    col={"xs": 12, "sm": 6},
                ),
                _compact_value(
                    ft.Icons.AIR,
                    "Permanência na secagem",
                    self.drying_duration,
                    self.drying_duration_detail,
                    col={"xs": 12, "sm": 6},
                ),
            ],
        )
        self.table17_host.content = build_table17_preview(None, compact=True)
        return glass_surface(
            ft.Column(
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.ResponsiveRow(
                        spacing=12,
                        run_spacing=8,
                        controls=[
                            ft.Container(
                                col={"xs": 12, "sm": 8},
                                content=ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text(
                                            "Prévia da condição",
                                            size=16,
                                            weight=ft.FontWeight.BOLD,
                                            color=AppColors.TEXT_PRIMARY,
                                        ),
                                        ft.Text(
                                            "Configuração que será gravada no ensaio.",
                                            size=10,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                ),
                            ),
                            ft.Container(
                                col={"xs": 12, "sm": 4},
                                alignment=ft.Alignment.CENTER_RIGHT,
                                content=ft.Container(
                                    border_radius=18,
                                    gradient=ft.LinearGradient(
                                        begin=ft.Alignment.TOP_LEFT,
                                        end=ft.Alignment.BOTTOM_RIGHT,
                                        colors=[AppColors.PRIMARY, "#0F766E"],
                                    ),
                                    padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                                    content=self.ts_value,
                                ),
                            ),
                        ],
                    ),
                    condition_cards,
                    ft.ExpansionTile(
                        title=ft.Text(
                            "Secagem",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                        subtitle=ft.Text(
                            "Abra para consultar a etapa posterior quando aplicável",
                            size=9,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        leading=ft.Icons.AIR,
                        maintain_state=True,
                        controls=[ft.Container(padding=10, content=drying_cards)],
                    ),
                    self.rule_reference,
                    self.table17_host,
                ],
            ),
            padding=18,
        )

    def _build(self) -> ft.Column:
        left: list[ft.Control] = [self._identity_panel(), self._notes_panel()]
        if self._details:
            left.append(
                glass_surface(
                    ft.Column(
                        spacing=7,
                        controls=[
                            ft.Text(
                                "Motivo da alteração",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            self.change_reason_selector.control,
                        ],
                    ),
                    padding=16,
                )
            )

        header = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
            run_spacing=8,
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
                            (
                                "Corrija os dados e registre a justificativa."
                                if self._details
                                else "Preencha o essencial; a norma é aplicada em tempo real."
                            ),
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
        )
        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                header,
                self.error_banner,
                *(
                    [
                        ft.Container(
                            border_radius=12,
                            bgcolor=AppColors.WARNING_LIGHT,
                            padding=12,
                            content=ft.Text(
                                "Alterações térmicas recalculam a condição e preservam os valores "
                                "anteriores no histórico.",
                                size=11,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                        )
                    ]
                    if self._details
                    else []
                ),
                ft.ResponsiveRow(
                    spacing=14,
                    run_spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Container(
                            col={"xs": 12, "xl": 5},
                            content=ft.Column(
                                spacing=14,
                                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                                controls=left,
                            ),
                        ),
                        ft.Container(
                            col={"xs": 12, "xl": 7},
                            content=self._thermal_panel(),
                        ),
                    ],
                ),
                self.result_panel,
                ft.Container(height=6),
            ],
        )

    def _display_condition(self, condition) -> None:
        super()._display_condition(condition)
        self.table17_host.content = build_table17_preview(condition.rule_id, compact=True)

    def _clear_condition(self, help_text: str) -> None:
        super()._clear_condition(help_text)
        if hasattr(self, "table17_host"):
            self.table17_host.content = build_table17_preview(None, compact=True)


def build_polished_new_test_view(*, on_cancel, on_save, draft: NewTestDraft | None = None):
    return PolishedNewTestView(on_cancel=on_cancel, on_save=on_save, draft=draft).root


def build_polished_edit_test_view(details: ClimateTestDetails, *, on_cancel, on_save):
    return PolishedNewTestView(
        on_cancel=on_cancel,
        on_save=on_save,
        details=details,
    ).root
