"""Detalhes de ensaio com foco em leitura rápida e ações próximas do contexto."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import flet as ft

from climatetest_manager.services.climate_tests import ClimateTestDetails
from climatetest_manager.ui.components import dialog_actions, dialog_banner, styled_dialog
from climatetest_manager.ui.components.table17 import build_table17_preview
from climatetest_manager.ui.formatters import format_decimal, format_duration_detail
from climatetest_manager.ui.interaction import glass_surface
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.ui.views.test_details import TestDetailsView


def _condition_pill(icon: ft.IconData, label: str, value: str) -> ft.Container:
    return ft.Container(
        col={"xs": 12, "sm": 4},
        border_radius=12,
        bgcolor=AppColors.SURFACE,
        border=ft.Border.all(1, AppColors.DIVIDER),
        padding=12,
        content=ft.Row(
            spacing=8,
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
                ft.Column(
                    expand=True,
                    spacing=1,
                    controls=[
                        ft.Text(label, size=9, color=AppColors.TEXT_SECONDARY),
                        ft.Text(
                            value,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                    ],
                ),
            ],
        ),
    )


class PolishedTestDetailsView(TestDetailsView):
    """Reutiliza regras/diálogos existentes e reduz a densidade da página principal."""

    def __init__(
        self,
        details: ClimateTestDetails,
        *,
        on_back: Callable[[], None],
        on_start_chamber,
        on_start_drying,
        on_finish,
        on_cancel,
        on_edit: Callable[[], None],
        on_delete,
        on_change_timestamp,
        on_admin_delete: Callable[[str], None] | None = None,
        on_advance_for_testing=None,
        read_only: bool = False,
    ) -> None:
        self._polished_on_back = on_back
        self._polished_on_edit = on_edit
        self._polished_admin_delete = on_admin_delete
        self._read_only = read_only
        super().__init__(
            details,
            on_back=on_back,
            on_start_chamber=on_start_chamber,
            on_start_drying=on_start_drying,
            on_finish=on_finish,
            on_cancel=on_cancel,
            on_edit=on_edit,
            on_delete=on_delete,
            on_change_timestamp=on_change_timestamp,
            on_advance_for_testing=on_advance_for_testing,
        )
        self.root = self._build_polished_root()

    def _build_polished_root(self) -> ft.Column:
        details = self._details
        header_actions: list[ft.Control] = []
        if not self._read_only:
            header_actions.append(
                ft.Button(
                    content="Corrigir dados",
                    icon=ft.Icons.EDIT_OUTLINED,
                    on_click=lambda _event: self._polished_on_edit(),
                )
            )
        if not self._read_only and any(
            (
                details.chamber_started_at,
                details.chamber_ended_at,
                details.drying_started_at,
                details.drying_ended_at,
            )
        ):
            header_actions.append(
                ft.Button(
                    content="Corrigir horários",
                    icon=ft.Icons.EDIT_CALENDAR_OUTLINED,
                    on_click=lambda _event: self._show_change_timestamps(),
                )
            )
        if self._polished_admin_delete is not None:
            header_actions.append(
                ft.Button(
                    content="Excluir do histórico",
                    icon=ft.Icons.DELETE_OUTLINE,
                    color=AppColors.DANGER,
                    tooltip="Disponível somente para administradores",
                    on_click=lambda _event: self._show_admin_delete_dialog(),
                )
            )

        header = ft.ResponsiveRow(
            spacing=12,
            run_spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    col={"xs": 12, "lg": 7},
                    content=ft.Row(
                        spacing=10,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                tooltip="Voltar para Ensaios",
                                on_click=lambda _event: self._polished_on_back(),
                            ),
                            ft.Column(
                                expand=True,
                                spacing=2,
                                controls=[
                                    ft.Text(
                                        f"{details.client} / {details.process_number}",
                                        size=25,
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        f"Ensaio #{details.id} • {details.product}",
                                        size=11,
                                        color=AppColors.TEXT_SECONDARY,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
                ft.Container(
                    col={"xs": 12, "lg": 5},
                    alignment=ft.Alignment.CENTER_RIGHT,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        wrap=True,
                        run_spacing=7,
                        controls=header_actions,
                    ),
                ),
            ],
        )
        return ft.ListView(
            expand=True,
            spacing=15,
            controls=[
                header,
                self._summary_panel(),
                self._journey_panel(),
                self._phase_panel(),
                self._action_panel(),
                ft.ExpansionTile(
                    title=ft.Text(
                        "Registro técnico detalhado",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    subtitle=ft.Text(
                        "Histórico completo de alterações e responsáveis",
                        size=10,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    leading=ft.Icon(ft.Icons.HISTORY),
                    maintain_state=True,
                    controls=[ft.Container(padding=8, content=self._history_panel())],
                ),
                ft.Container(height=6),
            ],
        )

    def _phase_panel(self) -> ft.Container:
        details = self._details
        chamber = ft.ResponsiveRow(
            spacing=9,
            run_spacing=9,
            controls=[
                _condition_pill(
                    ft.Icons.THERMOSTAT,
                    "Temperatura",
                    f"{format_decimal(details.chamber_temperature_c)} ± 2 °C",
                ),
                _condition_pill(
                    ft.Icons.WATER_DROP_OUTLINED,
                    "Umidade",
                    f"{format_decimal(details.chamber_humidity_percent)} ± 5% UR",
                ),
                _condition_pill(
                    ft.Icons.SCHEDULE,
                    "Permanência",
                    (
                        f"{details.chamber_duration_hours} h "
                        f"(+{details.chamber_duration_tolerance_hours} h)"
                    ),
                ),
            ],
        )
        schedule = ft.ResponsiveRow(
            spacing=9,
            run_spacing=9,
            controls=[
                _condition_pill(
                    ft.Icons.LOGIN,
                    "Entrada",
                    self._format_datetime_or_pending(details.chamber_started_at),
                ),
                _condition_pill(
                    ft.Icons.EVENT_AVAILABLE,
                    "Retirada nominal",
                    self._format_datetime_or_pending(details.chamber_nominal_end_at),
                ),
                _condition_pill(
                    ft.Icons.WARNING_AMBER,
                    "Limite",
                    self._format_datetime_or_pending(details.chamber_maximum_end_at),
                ),
            ],
        )
        sections: list[ft.Control] = [
            ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.WATER_DROP_OUTLINED, color=AppColors.PRIMARY),
                    ft.Text(
                        "Câmara climática",
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                ],
            ),
            chamber,
            ft.Text(
                format_duration_detail(
                    details.chamber_duration_hours,
                    details.chamber_duration_tolerance_hours,
                ),
                size=9,
                color=AppColors.TEXT_SECONDARY,
            ),
            ft.ExpansionTile(
                title=ft.Text("Cronograma", size=12, weight=ft.FontWeight.BOLD),
                subtitle=ft.Text(
                    "Entrada, retirada recomendada e limite máximo",
                    size=9,
                    color=AppColors.TEXT_SECONDARY,
                ),
                leading=ft.Icon(ft.Icons.CALENDAR_MONTH_OUTLINED),
                maintain_state=True,
                controls=[ft.Container(padding=8, content=schedule)],
            ),
        ]
        if details.drying_required:
            sections.extend(
                [
                    ft.Divider(height=1, color=AppColors.DIVIDER),
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.AIR, color=AppColors.DRYING),
                            ft.Text(
                                "Secagem",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                        ],
                    ),
                    ft.ResponsiveRow(
                        spacing=9,
                        run_spacing=9,
                        controls=[
                            _condition_pill(
                                ft.Icons.THERMOSTAT,
                                "Temperatura",
                                f"{format_decimal(details.drying_temperature_c or 0)} ± 2 °C",
                            ),
                            _condition_pill(
                                ft.Icons.SCHEDULE,
                                "Permanência",
                                (
                                    f"{details.drying_duration_hours} h "
                                    f"(+{details.drying_duration_tolerance_hours} h)"
                                ),
                            ),
                        ],
                    ),
                ]
            )
        sections.extend(
            [
                ft.Divider(height=1, color=AppColors.DIVIDER),
                build_table17_preview(details.rule_id, compact=False),
            ]
        )
        return glass_surface(
            ft.Column(
                spacing=11,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=sections,
            ),
            padding=18,
        )

    @staticmethod
    def _format_datetime_or_pending(value: datetime | None) -> str:
        if value is None:
            return "Pendente"
        return value.strftime("%d/%m/%Y %H:%M")

    def _action_panel(self) -> ft.Container:
        details = self._details
        if self._read_only:
            return glass_surface(
                ft.Row(
                    spacing=9,
                    controls=[
                        ft.Icon(ft.Icons.VISIBILITY_OUTLINED, color=AppColors.INFO),
                        ft.Text(
                            "Perfil de consulta: informações disponíveis somente para leitura.",
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
                padding=16,
            )
        active = {"Aguardando", "Na Câmara", "Em Secagem"}
        if details.situation not in active:
            return glass_surface(
                ft.Row(
                    spacing=9,
                    controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=AppColors.PRIMARY),
                        ft.Text(
                            "Ensaio encerrado: não há ações operacionais pendentes.",
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
                padding=16,
            )
        if details.is_paused:
            return glass_surface(
                dialog_banner(
                    "A contagem está pausada. Retome o equipamento no Dashboard antes de "
                    "registrar a próxima etapa.",
                    icon=ft.Icons.PAUSE_CIRCLE_OUTLINE,
                    warning=True,
                ),
                padding=16,
            )

        callback = None
        primary_label = ""
        primary_icon = ft.Icons.PLAY_ARROW
        if details.situation == "Aguardando":
            callback = self._confirm_chamber_start
            primary_label = "Registrar entrada agora"
        elif details.situation == "Na Câmara":
            if details.drying_required:
                callback = self._confirm_chamber_exit_to_drying
                primary_label = "Retirar e iniciar secagem"
                primary_icon = ft.Icons.AIR
            else:
                callback = self._confirm_chamber_exit_and_finish
                primary_label = "Retirar e finalizar"
                primary_icon = ft.Icons.CHECK
        else:
            callback = self._confirm_drying_exit_and_finish
            primary_label = "Retirar e finalizar"
            primary_icon = ft.Icons.CHECK

        action_callback = callback
        primary = ft.Button(
            content=primary_label,
            icon=primary_icon,
            bgcolor=AppColors.PRIMARY,
            color=AppColors.WHITE,
            height=46,
            on_click=(
                (lambda _event: action_callback(datetime.now().replace(microsecond=0)))
                if details.situation == "Aguardando"
                else (lambda _event: action_callback(None))
            ),
        )
        manual = ft.Button(
            content="Informar outro horário",
            icon=ft.Icons.EDIT_CALENDAR_OUTLINED,
            height=46,
            on_click=lambda _event: self._manual(action_callback),
        )
        danger = ft.Button(
            content="Cancelar ensaio",
            icon=ft.Icons.CANCEL_OUTLINED,
            color=AppColors.DANGER,
            on_click=lambda _event: self._show_cancel_dialog(),
        )
        return glass_surface(
            ft.Column(
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(
                                "Próxima ação",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            ft.Text(
                                "Registre em tempo real sempre que possível; use outro horário "
                                "somente para uma operação que já ocorreu.",
                                size=10,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=9,
                        wrap=True,
                        run_spacing=8,
                        controls=[primary, manual, danger],
                    ),
                ],
            ),
            padding=18,
            accent=True,
        )

    def _show_admin_delete_dialog(self) -> None:
        if self._polished_admin_delete is None:
            return
        page = self.root.page
        reason = ft.TextField(
            label="Motivo da exclusão *",
            hint_text="Ex.: cadastro duplicado confirmado pelo responsável",
            multiline=True,
            min_lines=2,
            max_lines=4,
            max_length=400,
        )
        error = ft.Text("", size=10, color=AppColors.DANGER)

        def confirm(_event: object | None = None) -> None:
            normalized = reason.value.strip()
            if len(normalized) < 10:
                error.value = "Informe um motivo com pelo menos 10 caracteres."
                error.update()
                return
            page.pop_dialog()
            self._polished_admin_delete(normalized)

        page.show_dialog(
            styled_dialog(
                title=f"Excluir ensaio #{self._details.id} do histórico?",
                subtitle="Apenas administradores podem executar esta ação",
                icon=ft.Icons.DELETE_FOREVER_OUTLINED,
                danger=True,
                content=ft.Column(
                    width=520,
                    tight=True,
                    spacing=10,
                    controls=[
                        dialog_banner(
                            "O ensaio deixará de aparecer nas telas operacionais. Um registro "
                            "de auditoria da exclusão será mantido para rastreabilidade.",
                            icon=ft.Icons.WARNING_AMBER,
                            danger=True,
                        ),
                        reason,
                        error,
                    ],
                ),
                actions=dialog_actions(
                    page=page,
                    primary_label="Excluir do histórico",
                    primary_icon=ft.Icons.DELETE_FOREVER_OUTLINED,
                    on_confirm=confirm,
                    danger=True,
                    cancel_label="Manter ensaio",
                ),
            )
        )


def build_polished_test_details_view(details: ClimateTestDetails, **kwargs) -> ft.Control:
    return PolishedTestDetailsView(details, **kwargs).root
