"""Cartão reutilizável para indicadores do dashboard."""

from collections.abc import Callable

import flet as ft

from climatetest_manager.ui.theme import AppColors


def metric_card(
    title: str,
    value: int,
    icon: ft.IconData,
    icon_color: str,
    icon_background: str,
    *,
    selected: bool = False,
    on_click: Callable[[], None] | None = None,
) -> ft.Container:
    """Cria um cartão compacto de métrica."""

    return ft.Container(
        col={"xs": 12, "sm": 6, "lg": 3},
        bgcolor=AppColors.SURFACE,
        border_radius=16,
        border=ft.Border.all(2, icon_color) if selected else None,
        padding=20,
        tooltip=(
            "Clique novamente para remover o filtro"
            if selected
            else "Clique para filtrar os ensaios por este indicador"
        )
        if on_click
        else None,
        on_click=(lambda _event: on_click()) if on_click else None,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text(title, size=13, color=AppColors.TEXT_SECONDARY),
                        ft.Text(
                            str(value),
                            size=30,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                    ],
                ),
                ft.Container(
                    width=46,
                    height=46,
                    border_radius=14,
                    bgcolor=icon_background,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, color=icon_color, size=24),
                ),
            ],
        ),
    )
