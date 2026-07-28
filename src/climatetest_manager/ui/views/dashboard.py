"""Dashboard operacional com recursos, ensaios ativos e progresso real."""

from collections.abc import Callable

import flet as ft

from climatetest_manager.services.climate_tests import (
    ClimateTestListItem,
    DashboardSummary,
    ResourceStatus,
)
from climatetest_manager.ui.components import metric_card
from climatetest_manager.ui.formatters import (
    format_condition_source,
    format_datetime,
    format_decimal,
)
from climatetest_manager.ui.theme import AppColors


def _empty_state(on_new_test: Callable[[], None]) -> ft.Container:
    return ft.Container(
        expand=True,
        bgcolor=AppColors.SURFACE,
        border_radius=16,
        padding=32,
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
            controls=[
                ft.Container(
                    width=64,
                    height=64,
                    border_radius=20,
                    bgcolor=AppColors.PRIMARY_LIGHT,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(ft.Icons.SCIENCE, color=AppColors.PRIMARY, size=30),
                ),
                ft.Text(
                    "Nenhum ensaio ativo",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                ft.Text(
                    "Finalizados e cancelados continuam disponíveis na tela Ensaios.",
                    size=13,
                    color=AppColors.TEXT_SECONDARY,
                ),
                ft.Button(
                    content="Cadastrar ensaio",
                    icon=ft.Icons.ADD,
                    color=AppColors.PRIMARY,
                    on_click=lambda _event: on_new_test(),
                ),
            ],
        ),
    )


def _status_style(test: ClimateTestListItem) -> tuple[str, str, str]:
    if test.is_paused:
        return "Pausado", AppColors.WARNING, AppColors.WARNING_LIGHT
    if test.situation == "Aguardando":
        return "Pendente de início", AppColors.INFO, AppColors.INFO_LIGHT
    if test.deadline_condition == "Atrasado":
        return "Atrasado", AppColors.DANGER, AppColors.DANGER_LIGHT
    if test.deadline_condition in {"Vence hoje", "Em tolerância"}:
        return test.deadline_condition, AppColors.WARNING, AppColors.WARNING_LIGHT
    return test.situation, AppColors.PRIMARY, AppColors.PRIMARY_LIGHT


def _active_tests(
    tests: list[ClimateTestListItem],
    on_new_test: Callable[[], None],
    on_select: Callable[[int], None],
) -> ft.Control:
    if not tests:
        return _empty_state(on_new_test)

    rows: list[ft.Control] = []
    for test in tests:
        status_text, status_color, status_background = _status_style(test)
        phase_detail = (
            test.pause_reason
            if test.is_paused
            else f"Retirar a partir de {format_datetime(test.nominal_end_at)}"
            if test.nominal_end_at
            else "Aguardando registro de entrada"
        )
        rows.append(
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=14,
                padding=16,
                on_click=lambda _event, test_id=test.id: on_select(test_id),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            expand=4,
                            content=ft.Row(
                                spacing=14,
                                controls=[
                                    ft.Container(
                                        width=42,
                                        height=42,
                                        border_radius=12,
                                        bgcolor=AppColors.PRIMARY_LIGHT,
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Icon(
                                            ft.Icons.SCIENCE,
                                            color=AppColors.PRIMARY,
                                            size=22,
                                        ),
                                    ),
                                    ft.Column(
                                        spacing=2,
                                        expand=True,
                                        controls=[
                                            ft.Text(
                                                test.client,
                                                size=14,
                                                weight=ft.FontWeight.BOLD,
                                                color=AppColors.TEXT_PRIMARY,
                                                max_lines=1,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            ),
                                            ft.Text(
                                                f"{test.process_number} • {test.product}",
                                                size=12,
                                                color=AppColors.TEXT_SECONDARY,
                                                max_lines=1,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            ),
                                            ft.Text(
                                                f"{test.sample_quantity} amostra(s) • "
                                                f"{format_condition_source(test.input_mode)}",
                                                size=10,
                                                color=AppColors.TEXT_SECONDARY,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            expand=3,
                            content=ft.Column(
                                spacing=3,
                                controls=[
                                    ft.Text(
                                        test.situation,
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        phase_detail or "Sem detalhe",
                                        size=10,
                                        color=AppColors.TEXT_SECONDARY,
                                        max_lines=2,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Text(
                                        "Câmara: "
                                        f"{format_decimal(test.chamber_temperature_c)} °C • "
                                        f"{format_decimal(test.chamber_humidity_percent)}% UR",
                                        size=10,
                                        color=AppColors.TEXT_SECONDARY,
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            width=230,
                            content=ft.Column(
                                spacing=6,
                                controls=[
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        controls=[
                                            ft.Text(
                                                "Progresso da etapa",
                                                size=10,
                                                color=AppColors.TEXT_SECONDARY,
                                            ),
                                            ft.Text(
                                                f"{test.progress_percent * 100:.0f}%",
                                                size=11,
                                                weight=ft.FontWeight.BOLD,
                                                color=status_color,
                                            ),
                                        ],
                                    ),
                                    ft.ProgressBar(
                                        value=test.progress_percent,
                                        width=230,
                                        height=8,
                                        color=status_color,
                                        bgcolor=AppColors.DIVIDER,
                                        border_radius=6,
                                    ),
                                    ft.Text(
                                        test.progress_label,
                                        size=10,
                                        color=AppColors.TEXT_SECONDARY,
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            width=145,
                            alignment=ft.Alignment.CENTER,
                            bgcolor=status_background,
                            border_radius=20,
                            padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                            content=ft.Text(
                                status_text,
                                size=10,
                                text_align=ft.TextAlign.CENTER,
                                weight=ft.FontWeight.BOLD,
                                color=status_color,
                            ),
                        ),
                    ],
                ),
            )
        )
    return ft.Column(spacing=10, controls=rows)


class DashboardView:
    """Mantém os diálogos de pausa próximos dos controles do equipamento."""

    def __init__(
        self,
        summary: DashboardSummary,
        active_tests: list[ClimateTestListItem],
        resource_statuses: tuple[ResourceStatus, ...],
        *,
        on_new_test: Callable[[], None],
        on_select: Callable[[int], None],
        on_pause_resource: Callable[[str, str], None],
        on_resume_resource: Callable[[str], None],
    ) -> None:
        self._on_pause_resource = on_pause_resource
        self.root = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Column(
                            spacing=3,
                            controls=[
                                ft.Text(
                                    "Visão geral",
                                    size=28,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    "Somente pendentes, pausados e ensaios em andamento.",
                                    size=14,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                        ft.Button(
                            content="Novo ensaio",
                            icon=ft.Icons.ADD,
                            bgcolor=AppColors.PRIMARY,
                            color=AppColors.WHITE,
                            on_click=lambda _event: on_new_test(),
                        ),
                    ],
                ),
                ft.Row(
                    spacing=16,
                    controls=[
                        metric_card(
                            "Em andamento",
                            summary.in_progress,
                            ft.Icons.PLAY_ARROW,
                            AppColors.PRIMARY,
                            AppColors.PRIMARY_LIGHT,
                        ),
                        metric_card(
                            "Pendentes de início",
                            summary.waiting,
                            ft.Icons.PENDING_ACTIONS,
                            AppColors.INFO,
                            AppColors.INFO_LIGHT,
                        ),
                        metric_card(
                            "Pausados",
                            summary.paused,
                            ft.Icons.PAUSE_CIRCLE,
                            AppColors.WARNING,
                            AppColors.WARNING_LIGHT,
                        ),
                        metric_card(
                            "Atrasados",
                            summary.overdue,
                            ft.Icons.WARNING,
                            AppColors.DANGER,
                            AppColors.DANGER_LIGHT,
                        ),
                    ],
                ),
                ft.Text(
                    "Controle dos equipamentos",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                ft.Row(
                    spacing=14,
                    controls=[
                        self._resource_card(status, on_resume_resource)
                        for status in resource_statuses
                    ],
                ),
                ft.Text(
                    "Ensaios ativos",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                _active_tests(active_tests, on_new_test, on_select),
                ft.Container(height=8),
            ],
        )

    def _resource_card(
        self,
        status: ResourceStatus,
        on_resume_resource: Callable[[str], None],
    ) -> ft.Container:
        color = AppColors.WARNING if status.is_paused else AppColors.PRIMARY
        background = AppColors.WARNING_LIGHT if status.is_paused else AppColors.PRIMARY_LIGHT
        detail = (
            f"Desde {format_datetime(status.paused_at)} • "
            f"{status.affected_count} ensaio(s) afetado(s)\n"
            f"Motivo: {status.reason}"
            if status.is_paused
            else "Disponível para iniciar e continuar ensaios."
        )
        button = (
            ft.Button(
                content="Retomar",
                icon=ft.Icons.PLAY_ARROW,
                bgcolor=AppColors.PRIMARY,
                color=AppColors.WHITE,
                on_click=lambda _event: on_resume_resource(status.resource),
            )
            if status.is_paused
            else ft.Button(
                content="Pausar",
                icon=ft.Icons.PAUSE,
                color=AppColors.WARNING,
                on_click=lambda _event: self._show_pause_dialog(
                    status.resource,
                    status.label,
                ),
            )
        )
        return ft.Container(
            expand=True,
            bgcolor=AppColors.SURFACE,
            border_radius=14,
            padding=16,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=12,
                        expand=True,
                        controls=[
                            ft.Container(
                                width=42,
                                height=42,
                                border_radius=12,
                                bgcolor=background,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(
                                    ft.Icons.PAUSE_CIRCLE
                                    if status.is_paused
                                    else ft.Icons.CHECK_CIRCLE,
                                    color=color,
                                ),
                            ),
                            ft.Column(
                                spacing=3,
                                expand=True,
                                controls=[
                                    ft.Text(
                                        status.label,
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        "Pausada" if status.is_paused else "Em operação",
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                        color=color,
                                    ),
                                    ft.Text(
                                        detail,
                                        size=10,
                                        color=AppColors.TEXT_SECONDARY,
                                        max_lines=3,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    button,
                ],
            ),
        )

    def _show_pause_dialog(self, resource: str, label: str) -> None:
        reason = ft.TextField(
            label="Motivo obrigatório",
            hint_text="Ex.: câmara em manutenção",
            multiline=True,
            min_lines=2,
            max_lines=3,
            autofocus=True,
        )
        page = self.root.page

        def confirm(_event: object | None = None) -> None:
            normalized = reason.value.strip()
            if not normalized:
                reason.error = "Informe por que o equipamento será pausado."
                reason.update()
                return
            page.pop_dialog()
            self._on_pause_resource(resource, normalized)

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Pausar {label.lower()}?"),
                content=ft.Column(
                    tight=True,
                    spacing=10,
                    controls=[
                        ft.Text(
                            "Todos os ensaios atualmente nesse equipamento terão a "
                            "contagem congelada até a retomada."
                        ),
                        reason,
                    ],
                ),
                actions=[
                    ft.TextButton(
                        content="Não",
                        on_click=lambda _event: page.pop_dialog(),
                    ),
                    ft.TextButton(
                        content="Sim, pausar",
                        on_click=confirm,
                        style=ft.ButtonStyle(color=AppColors.WARNING),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )


def build_dashboard(
    summary: DashboardSummary,
    active_tests: list[ClimateTestListItem],
    resource_statuses: tuple[ResourceStatus, ...],
    *,
    on_new_test: Callable[[], None],
    on_select: Callable[[int], None],
    on_pause_resource: Callable[[str, str], None],
    on_resume_resource: Callable[[str], None],
) -> ft.Column:
    """Monta o resumo operacional sem finalizados ou cancelados."""

    return DashboardView(
        summary,
        active_tests,
        resource_statuses,
        on_new_test=on_new_test,
        on_select=on_select,
        on_pause_resource=on_pause_resource,
        on_resume_resource=on_resume_resource,
    ).root
