"""Tela pesquisável dos ensaios cadastrados."""

from collections.abc import Awaitable, Callable

import flet as ft

from climatetest_manager.services.climate_tests import ClimateTestListItem
from climatetest_manager.ui.formatters import (
    format_condition_source,
    format_datetime,
    format_thermal_summary,
)
from climatetest_manager.ui.theme import AppColors


def _badge(
    text: str,
    *,
    danger: bool = False,
    warning: bool = False,
) -> ft.Container:
    background = (
        AppColors.DANGER_LIGHT
        if danger
        else AppColors.WARNING_LIGHT
        if warning
        else AppColors.INFO_LIGHT
    )
    color = AppColors.DANGER if danger else AppColors.WARNING if warning else AppColors.INFO
    return ft.Container(
        border_radius=18,
        bgcolor=background,
        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
        content=ft.Text(
            text,
            size=11,
            weight=ft.FontWeight.BOLD,
            color=color,
        ),
    )


class TestsListView:
    """Mantém pesquisa e filtro locais sem consultar o banco a cada tecla."""

    def __init__(
        self,
        tests: list[ClimateTestListItem],
        *,
        on_select: Callable[[int], None],
        on_new_test: Callable[[], None],
        on_export: Callable[[list[ClimateTestListItem]], Awaitable[None]],
    ) -> None:
        self._tests = tests
        self._on_select = on_select
        self._on_export = on_export
        self.search = ft.TextField(
            hint_text="Pesquisar cliente, processo ou produto",
            prefix_icon=ft.Icons.SEARCH,
            border_radius=10,
            border_color=AppColors.DIVIDER,
            bgcolor=AppColors.SURFACE,
            on_change=self._refresh,
            expand=True,
        )
        situations = sorted({item.situation for item in tests})
        self.filter = ft.Dropdown(
            value="Todos",
            options=[ft.DropdownOption(key="Todos", text="Todas as situações")]
            + [ft.DropdownOption(key=item, text=item) for item in situations],
            border_radius=10,
            border_color=AppColors.DIVIDER,
            bgcolor=AppColors.SURFACE,
            on_select=self._refresh,
            width=220,
        )
        self.results = ft.Column(spacing=10)
        self.result_count = ft.Text("", size=11, color=AppColors.TEXT_SECONDARY)
        self.root = ft.Column(
            expand=True,
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=3,
                            controls=[
                                ft.Text(
                                    "Ensaios",
                                    size=28,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    "Pesquise registros e acompanhe cada etapa operacional.",
                                    size=14,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                        ft.Row(
                            controls=[
                                ft.Button(
                                    content="Exportar resultados (CSV)",
                                    icon=ft.Icons.DOWNLOAD,
                                    on_click=self._export_matching,
                                ),
                                ft.Button(
                                    content="Novo ensaio",
                                    icon=ft.Icons.ADD,
                                    bgcolor=AppColors.PRIMARY,
                                    color=AppColors.WHITE,
                                    on_click=lambda _event: on_new_test(),
                                ),
                            ]
                        ),
                    ],
                ),
                ft.Row(spacing=12, controls=[self.search, self.filter]),
                self.result_count,
                self.results,
            ],
        )
        self._refresh()

    def _matching(self) -> list[ClimateTestListItem]:
        query = self.search.value.strip().casefold()
        selected = self.filter.value or "Todos"
        return [
            item
            for item in self._tests
            if (selected == "Todos" or item.situation == selected)
            and (
                not query
                or query in item.client.casefold()
                or query in item.process_number.casefold()
                or query in item.product.casefold()
            )
        ]

    def _refresh(self, _event: object | None = None) -> None:
        matching = self._matching()
        self.result_count.value = (
            f"{len(matching)} resultado" if len(matching) == 1 else f"{len(matching)} resultados"
        )
        if not matching:
            self.results.controls = [
                ft.Container(
                    bgcolor=AppColors.SURFACE,
                    border_radius=14,
                    padding=28,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text("Nenhum ensaio encontrado.", color=AppColors.TEXT_SECONDARY),
                )
            ]
        else:
            self.results.controls = [self._row(item) for item in matching]
        try:
            _page = self.root.page
        except RuntimeError:
            return
        self.result_count.update()
        self.results.update()

    async def _export_matching(self, _event: object | None = None) -> None:
        await self._on_export(self._matching())

    def _row(self, item: ClimateTestListItem) -> ft.Container:
        deadline = item.deadline_condition or "Sem prazo ativo"
        deadline_text = (
            f"{deadline} • nominal {format_datetime(item.nominal_end_at)}"
            if item.nominal_end_at
            else deadline
        )
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border_radius=14,
            padding=16,
            on_click=lambda _event, test_id=item.id: self._on_select(test_id),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Container(
                        expand=4,
                        content=ft.Column(
                            spacing=3,
                            controls=[
                                ft.Text(
                                    f"#{item.id} • {item.client}",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    f"{item.process_number} • {item.product}",
                                    size=12,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                    ),
                    ft.Container(
                        expand=3,
                        alignment=ft.Alignment.CENTER_LEFT,
                        content=ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text(
                                    f"{item.sample_quantity} amostra(s) • "
                                    f"{format_condition_source(item.input_mode)}",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    format_thermal_summary(
                                        input_mode=item.input_mode,
                                        epl=item.epl,
                                        service_temperature_c=(item.service_temperature_c),
                                        ts_reference=item.ts_reference,
                                        selected_option=item.selected_option,
                                    ),
                                    size=11,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                    ),
                    ft.Container(
                        width=210,
                        alignment=ft.Alignment.CENTER_RIGHT,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            spacing=4,
                            controls=[
                                _badge(
                                    (
                                        f"Pausado — {item.situation}"
                                        if item.is_paused
                                        else item.situation
                                    ),
                                    danger=item.situation == "Cancelado",
                                    warning=item.is_paused,
                                ),
                                ft.Text(
                                    deadline_text,
                                    size=11,
                                    color=(
                                        AppColors.DANGER
                                        if deadline == "Atrasado"
                                        else AppColors.TEXT_SECONDARY
                                    ),
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )


def build_tests_list_view(
    tests: list[ClimateTestListItem],
    *,
    on_select: Callable[[int], None],
    on_new_test: Callable[[], None],
    on_export: Callable[[list[ClimateTestListItem]], Awaitable[None]],
) -> ft.Column:
    """Cria uma lista nova com pesquisa e filtro."""

    return TestsListView(
        tests,
        on_select=on_select,
        on_new_test=on_new_test,
        on_export=on_export,
    ).root
