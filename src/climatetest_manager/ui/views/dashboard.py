"""Dashboard operacional com recursos, ensaios ativos e progresso real."""

from collections.abc import Callable

import flet as ft

from climatetest_manager.services.climate_tests import (
    ClimateTestListItem,
    DashboardSummary,
    ResourceStatus,
)
from climatetest_manager.ui.components import (
    ReasonSelector,
    dialog_actions,
    dialog_banner,
    metric_card,
    styled_dialog,
)
from climatetest_manager.ui.formatters import (
    format_condition_source,
    format_datetime,
    format_decimal,
)
from climatetest_manager.ui.theme import AppColors

PAUSE_REASON_OPTIONS = (
    "Manutenção preventiva ou corretiva",
    "Falta de energia",
    "Falha do equipamento",
    "Calibração ou verificação",
    "Indisponibilidade operacional",
)


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
                content=ft.ResponsiveRow(
                    spacing=14,
                    run_spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            col={"xs": 12, "md": 6, "lg": 4},
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
                                                f"{test.client} / {test.process_number}",
                                                size=14,
                                                weight=ft.FontWeight.BOLD,
                                                color=AppColors.TEXT_PRIMARY,
                                            ),
                                            ft.Text(
                                                f"Ensaio #{test.id} • {test.product}",
                                                size=12,
                                                color=AppColors.TEXT_SECONDARY,
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
                            col={"xs": 12, "md": 6, "lg": 3},
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
                            col={"xs": 12, "md": 8, "lg": 3},
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
                            col={"xs": 12, "md": 4, "lg": 2},
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
        self._summary = summary
        self._active_tests = active_tests
        self._on_new_test = on_new_test
        self._on_select = on_select
        self._active_filter: str | None = None
        self.metrics = ft.ResponsiveRow(spacing=16, run_spacing=16)
        self.results_title = ft.Text(
            "Ensaios ativos",
            size=18,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )
        self.results = ft.Container(content=_active_tests(active_tests, on_new_test, on_select))
        self._refresh_filter(update=False)
        self.root = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    wrap=True,
                    run_spacing=10,
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
                self.metrics,
                ft.Text(
                    "Controle dos equipamentos",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                ft.ResponsiveRow(
                    spacing=14,
                    run_spacing=14,
                    controls=[
                        self._resource_card(status, on_resume_resource)
                        for status in resource_statuses
                    ],
                ),
                self.results_title,
                self.results,
                ft.Container(height=8),
            ],
        )

    def _metric_cards(self) -> list[ft.Control]:
        definitions = [
            (
                "in_progress",
                "Em andamento",
                self._summary.in_progress,
                ft.Icons.PLAY_ARROW,
                AppColors.PRIMARY,
                AppColors.PRIMARY_LIGHT,
            ),
            (
                "waiting",
                "Pendentes de início",
                self._summary.waiting,
                ft.Icons.PENDING_ACTIONS,
                AppColors.INFO,
                AppColors.INFO_LIGHT,
            ),
            (
                "paused",
                "Pausados",
                self._summary.paused,
                ft.Icons.PAUSE_CIRCLE,
                AppColors.WARNING,
                AppColors.WARNING_LIGHT,
            ),
            (
                "overdue",
                "Atrasados",
                self._summary.overdue,
                ft.Icons.WARNING,
                AppColors.DANGER,
                AppColors.DANGER_LIGHT,
            ),
        ]
        return [
            metric_card(
                title,
                value,
                icon,
                color,
                background,
                selected=self._active_filter == key,
                on_click=lambda selected=key: self._select_filter(selected),
            )
            for key, title, value, icon, color, background in definitions
        ]

    def _select_filter(self, selected: str) -> None:
        self._active_filter = None if self._active_filter == selected else selected
        self._refresh_filter(update=True)

    def _refresh_filter(self, *, update: bool) -> None:
        selected = self._active_filter
        filtered = self._active_tests
        label = "Ensaios ativos"
        if selected == "in_progress":
            filtered = [
                item
                for item in filtered
                if item.situation in {"Na Câmara", "Em Secagem"} and not item.is_paused
            ]
            label = "Filtro: em andamento"
        elif selected == "waiting":
            filtered = [item for item in filtered if item.situation == "Aguardando"]
            label = "Filtro: pendentes de início"
        elif selected == "paused":
            filtered = [item for item in filtered if item.is_paused]
            label = "Filtro: pausados"
        elif selected == "overdue":
            filtered = [item for item in filtered if item.deadline_condition == "Atrasado"]
            label = "Filtro: atrasados"
        self.metrics.controls = self._metric_cards()
        self.results_title.value = label
        self.results.content = _active_tests(
            filtered,
            self._on_new_test,
            self._on_select,
        )
        if update:
            self.metrics.update()
            self.results_title.update()
            self.results.update()

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
                content=ft.Text("Retomar", no_wrap=True, max_lines=1),
                icon=ft.Icons.PLAY_ARROW,
                width=124,
                bgcolor=AppColors.PRIMARY,
                color=AppColors.WHITE,
                on_click=lambda _event: on_resume_resource(status.resource),
            )
            if status.is_paused
            else ft.Button(
                content=ft.Text("Pausar", no_wrap=True, max_lines=1),
                icon=ft.Icons.PAUSE,
                width=124,
                color=AppColors.WARNING,
                on_click=lambda _event: self._show_pause_dialog(
                    status.resource,
                    status.label,
                ),
            )
        )
        return ft.Container(
            col={"xs": 12, "lg": 6},
            bgcolor=AppColors.SURFACE,
            border_radius=14,
            padding=16,
            content=ft.ResponsiveRow(
                spacing=12,
                run_spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        col={"xs": 12, "md": 8},
                        content=ft.Row(
                            spacing=12,
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
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    ft.Container(
                        col={"xs": 12, "md": 4},
                        alignment=ft.Alignment.CENTER_RIGHT,
                        content=button,
                    ),
                ],
            ),
        )

    def _show_pause_dialog(self, resource: str, label: str) -> None:
        reason_selector = ReasonSelector(
            PAUSE_REASON_OPTIONS,
            other_hint="Resuma por que o equipamento será pausado",
        )
        page = self.root.page

        def confirm(_event: object | None = None) -> None:
            if not reason_selector.validate(message="Selecione o motivo da pausa."):
                return
            page.pop_dialog()
            self._on_pause_resource(resource, reason_selector.value())

        page.show_dialog(
            styled_dialog(
                title=f"Pausar {label.lower()}?",
                subtitle="A contagem será congelada para todos os ensaios afetados",
                icon=ft.Icons.PAUSE_CIRCLE_OUTLINE,
                danger=True,
                content=ft.Column(
                    width=560,
                    tight=True,
                    spacing=14,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        dialog_banner(
                            "Os prazos deixam de avançar até a retomada. Depois, o sistema "
                            "desloca automaticamente as retiradas nominal e máxima.",
                            icon=ft.Icons.TIMER_OFF_OUTLINED,
                            warning=True,
                        ),
                        reason_selector.control,
                    ],
                ),
                actions=dialog_actions(
                    page=page,
                    primary_label="Confirmar pausa",
                    primary_icon=ft.Icons.PAUSE,
                    on_confirm=confirm,
                    danger=True,
                ),
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
