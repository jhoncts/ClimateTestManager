"""Cartão reutilizável para indicadores do dashboard."""

import flet as ft

from climatetest_manager.ui.theme import AppColors


def metric_card(
    title: str,
    value: int,
    icon: ft.IconData,
    icon_color: str,
    icon_background: str,
) -> ft.Container:
    """Cria um cartão compacto de métrica."""

    return ft.Container(
        expand=True,
        bgcolor=AppColors.SURFACE,
        border_radius=16,
        padding=20,
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
