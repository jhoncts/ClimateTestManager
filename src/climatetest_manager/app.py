"""Configuração da janela principal da aplicação."""

import flet as ft

from climatetest_manager import __version__
from climatetest_manager.database.session import initialize_database
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.ui.views.dashboard import build_dashboard


def _navigation_item(label: str, icon: ft.IconData, *, selected: bool = False) -> ft.Container:
    """Cria um item visual da navegação lateral."""

    return ft.Container(
        border_radius=10,
        bgcolor=AppColors.NAV_SELECTED if selected else AppColors.NAV_BACKGROUND,
        padding=12,
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


def _build_sidebar() -> ft.Container:
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
                _navigation_item("Dashboard", ft.Icons.DASHBOARD, selected=True),
                _navigation_item("Ensaios", ft.Icons.LIST),
                _navigation_item("Novo ensaio", ft.Icons.ADD),
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


def _build_shell() -> ft.Row:
    """Combina a navegação e o conteúdo da tela atual."""

    return ft.Row(
        expand=True,
        spacing=0,
        controls=[
            _build_sidebar(),
            ft.Container(
                expand=True,
                bgcolor=AppColors.PAGE_BACKGROUND,
                padding=32,
                content=build_dashboard(),
            ),
        ],
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
        initialize_database()
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

    page.add(_build_shell())
