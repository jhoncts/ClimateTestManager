"""Dashboard conectado aos dados persistidos."""

from collections.abc import Callable

import flet as ft

from climatetest_manager.repositories.climate_tests import RecentClimateTest
from climatetest_manager.services.climate_tests import DashboardSummary
from climatetest_manager.ui.components import metric_card
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
                    "Nenhum ensaio em andamento",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                ft.Text(
                    "Cadastre o primeiro ensaio para começar o acompanhamento.",
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


def _recent_tests(tests: list[RecentClimateTest], on_new_test: Callable[[], None]) -> ft.Control:
    if not tests:
        return _empty_state(on_new_test)

    rows: list[ft.Control] = []
    for test in tests:
        rows.append(
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=14,
                padding=16,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=14,
                            controls=[
                                ft.Container(
                                    width=42,
                                    height=42,
                                    border_radius=12,
                                    bgcolor=AppColors.PRIMARY_LIGHT,
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(
                                        ft.Icons.SCIENCE, color=AppColors.PRIMARY, size=22
                                    ),
                                ),
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text(
                                            test.client,
                                            size=14,
                                            weight=ft.FontWeight.BOLD,
                                            color=AppColors.TEXT_PRIMARY,
                                        ),
                                        ft.Text(
                                            f"{test.process_number} • {test.product}",
                                            size=12,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.Text(
                            f"EPL {test.epl}  •  Ts {test.service_temperature_c} °C  •  "
                            f"Opção {test.selected_option}",
                            size=12,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        ft.Container(
                            bgcolor=AppColors.WARNING_LIGHT,
                            border_radius=20,
                            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                            content=ft.Text(
                                test.situation,
                                size=11,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.WARNING,
                            ),
                        ),
                    ],
                ),
            )
        )
    return ft.Column(spacing=10, controls=rows)


def build_dashboard(
    summary: DashboardSummary,
    recent_tests: list[RecentClimateTest],
    *,
    on_new_test: Callable[[], None],
) -> ft.Column:
    """Monta o dashboard com os indicadores e cadastros mais recentes."""

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
                        on_click=lambda _event: on_new_test(),
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
                            "Cadastro conectado ao banco e à Tabela 17 da norma.",
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
                        summary.in_progress,
                        ft.Icons.PLAY_ARROW,
                        AppColors.INFO,
                        AppColors.INFO_LIGHT,
                    ),
                    metric_card(
                        "Atrasados",
                        summary.overdue,
                        ft.Icons.WARNING,
                        AppColors.DANGER,
                        AppColors.DANGER_LIGHT,
                    ),
                    metric_card(
                        "Saem hoje",
                        summary.due_today,
                        ft.Icons.TODAY,
                        AppColors.WARNING,
                        AppColors.WARNING_LIGHT,
                    ),
                    metric_card(
                        "Em secagem",
                        summary.drying,
                        ft.Icons.AIR,
                        AppColors.DRYING,
                        AppColors.DRYING_LIGHT,
                    ),
                ],
            ),
            ft.Row(
                controls=[
                    ft.Text(
                        "Ensaios recentes",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    )
                ]
            ),
            _recent_tests(recent_tests, on_new_test),
        ],
    )
