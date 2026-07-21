"""Configuração da janela principal da aplicação."""

from collections.abc import Callable

import flet as ft

from climatetest_manager import __version__
from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.climate_tests import ClimateTestRepository
from climatetest_manager.services.climate_tests import (
    ClimateTestService,
    CreateClimateTestCommand,
)
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.ui.views.dashboard import build_dashboard
from climatetest_manager.ui.views.new_test import build_new_test_view


def _navigation_item(
    label: str,
    icon: ft.IconData,
    *,
    selected: bool = False,
    on_click: Callable[[], None] | None = None,
) -> ft.Container:
    """Cria um item visual da navegação lateral."""

    return ft.Container(
        border_radius=10,
        bgcolor=AppColors.NAV_SELECTED if selected else AppColors.NAV_BACKGROUND,
        padding=12,
        opacity=1 if on_click or selected else 0.55,
        on_click=(lambda _event: on_click()) if on_click else None,
        content=ft.Row(
            spacing=12,
            controls=[
                ft.Icon(
                    icon,
                    size=20,
                    color=AppColors.PRIMARY if selected else AppColors.NAV_TEXT,
                ),
                ft.Text(
                    label,
                    size=14,
                    weight=ft.FontWeight.BOLD if selected else ft.FontWeight.NORMAL,
                    color=AppColors.PRIMARY if selected else AppColors.NAV_TEXT,
                ),
            ],
        ),
    )


def _build_sidebar(
    *,
    selected_view: str,
    on_dashboard: Callable[[], None],
    on_new_test: Callable[[], None],
) -> ft.Container:
    """Monta a identidade e a navegação principal."""

    return ft.Container(
        width=252,
        bgcolor=AppColors.NAV_BACKGROUND,
        padding=24,
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    spacing=12,
                    controls=[
                        ft.Container(
                            width=42,
                            height=42,
                            border_radius=12,
                            bgcolor=AppColors.PRIMARY,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.SCIENCE, color=AppColors.WHITE, size=24),
                        ),
                        ft.Column(
                            spacing=0,
                            controls=[
                                ft.Text(
                                    "ClimateTest",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    "Manager",
                                    size=13,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                    ],
                ),
                ft.Container(height=22),
                _navigation_item(
                    "Dashboard",
                    ft.Icons.DASHBOARD,
                    selected=selected_view == "dashboard",
                    on_click=on_dashboard,
                ),
                _navigation_item("Ensaios", ft.Icons.LIST),
                _navigation_item(
                    "Novo ensaio",
                    ft.Icons.ADD,
                    selected=selected_view == "new_test",
                    on_click=on_new_test,
                ),
                _navigation_item("Histórico", ft.Icons.HISTORY),
                ft.Container(expand=True),
                ft.Divider(height=1, color=AppColors.DIVIDER),
                ft.Text(
                    "ABNT NBR IEC 60079-0:2020",
                    size=11,
                    color=AppColors.TEXT_SECONDARY,
                ),
                ft.Text(
                    f"Versão {__version__}",
                    size=11,
                    color=AppColors.TEXT_SECONDARY,
                ),
            ],
        ),
    )


def _build_shell(
    content: ft.Control,
    *,
    selected_view: str,
    on_dashboard: Callable[[], None],
    on_new_test: Callable[[], None],
) -> ft.Row:
    """Combina a navegação e o conteúdo da tela atual."""

    return ft.Row(
        expand=True,
        spacing=0,
        controls=[
            _build_sidebar(
                selected_view=selected_view,
                on_dashboard=on_dashboard,
                on_new_test=on_new_test,
            ),
            ft.Container(
                expand=True,
                bgcolor=AppColors.PAGE_BACKGROUND,
                padding=32,
                content=content,
            ),
        ],
    )


class ClimateTestApplication:
    """Controla navegação e casos de uso sem colocar regras na interface."""

    def __init__(self, page: ft.Page, service: ClimateTestService) -> None:
        self._page = page
        self._service = service

    def start(self) -> None:
        self.show_dashboard()

    def _render(self, content: ft.Control, *, selected_view: str) -> None:
        self._page.clean()
        self._page.add(
            _build_shell(
                content,
                selected_view=selected_view,
                on_dashboard=self.show_dashboard,
                on_new_test=self.show_new_test,
            )
        )
        self._page.update()

    def show_dashboard(self) -> None:
        content = build_dashboard(
            self._service.dashboard_summary(),
            self._service.list_recent(),
            on_new_test=self.show_new_test,
        )
        self._render(content, selected_view="dashboard")

    def show_new_test(self) -> None:
        content = build_new_test_view(
            on_cancel=self.show_dashboard,
            on_save=self._save_test,
        )
        self._render(content, selected_view="new_test")

    def _save_test(self, command: CreateClimateTestCommand) -> None:
        test_id = self._service.create(command)
        self.show_dashboard()
        self._page.show_dialog(
            ft.SnackBar(
                content=f"Ensaio #{test_id} cadastrado com sucesso.",
                bgcolor=AppColors.PRIMARY,
                show_close_icon=True,
            )
        )


def main(page: ft.Page) -> None:
    """Inicializa o banco local e apresenta a janela desktop."""

    page.title = "ClimateTest Manager"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=AppColors.PRIMARY)
    page.padding = 0
    page.spacing = 0
    page.bgcolor = AppColors.PAGE_BACKGROUND
    page.window.width = 1280
    page.window.height = 800
    page.window.min_width = 1000
    page.window.min_height = 680

    try:
        engine = initialize_database()
    except Exception as error:  # pragma: no cover - depende do sistema operacional
        page.add(
            ft.Container(
                padding=32,
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Não foi possível preparar o banco de dados.",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.DANGER,
                        ),
                        ft.Text(str(error), color=AppColors.TEXT_SECONDARY),
                    ]
                ),
            )
        )
        return

    repository = ClimateTestRepository(create_session_factory(engine))
    page.on_close = lambda _event: engine.dispose()
    ClimateTestApplication(page, ClimateTestService(repository)).start()
