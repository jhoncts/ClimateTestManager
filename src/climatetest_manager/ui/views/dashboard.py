"""Primeira versão visual do dashboard."""

import flet as ft

from climatetest_manager.ui.components import metric_card
from climatetest_manager.ui.theme import AppColors


def _empty_state() -> ft.Container:
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
                    "Nenhum ensaio em andamento",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                ft.Text(
                    "Os ensaios ativos e as próximas ações aparecerão aqui.",
                    size=13,
                    color=AppColors.TEXT_SECONDARY,
                ),
            ],
        ),
    )


def build_dashboard() -> ft.Column:
    """Monta o dashboard inicial com indicadores ainda zerados."""

    return ft.Column(
        expand=True,
        spacing=24,
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
                                "Acompanhe os ensaios e as próximas ações do laboratório.",
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
                        disabled=True,
                    ),
                ],
            ),
            ft.Container(
                border_radius=12,
                bgcolor=AppColors.INFO_LIGHT,
                padding=14,
                content=ft.Row(
                    spacing=10,
                    controls=[
                        ft.Icon(ft.Icons.INFO, color=AppColors.INFO, size=20),
                        ft.Text(
                            "Fundação concluída: banco local e regras normativas preparados.",
                            size=13,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                    ],
                ),
            ),
            ft.Row(
                spacing=16,
                controls=[
                    metric_card(
                        "Em andamento",
                        0,
                        ft.Icons.PLAY_ARROW,
                        AppColors.INFO,
                        AppColors.INFO_LIGHT,
                    ),
                    metric_card(
                        "Atrasados",
                        0,
                        ft.Icons.WARNING,
                        AppColors.DANGER,
                        AppColors.DANGER_LIGHT,
                    ),
                    metric_card(
                        "Saem hoje",
                        0,
                        ft.Icons.TODAY,
                        AppColors.WARNING,
                        AppColors.WARNING_LIGHT,
                    ),
                    metric_card(
                        "Em secagem",
                        0,
                        ft.Icons.AIR,
                        AppColors.DRYING,
                        AppColors.DRYING_LIGHT,
                    ),
                ],
            ),
            ft.Row(
                controls=[
                    ft.Text(
                        "Ensaios que exigem ação",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    )
                ]
            ),
            _empty_state(),
        ],
    )
