"""Consulta global do registro de atividades auditáveis."""

from collections.abc import Callable

import flet as ft

from climatetest_manager.repositories.climate_tests import AuditHistoryEntry
from climatetest_manager.ui.formatters import format_datetime
from climatetest_manager.ui.theme import AppColors


def build_history_view(
    events: list[AuditHistoryEntry],
    *,
    on_select: Callable[[int], None],
) -> ft.Column:
    """Monta o registro global e permite abrir o ensaio de origem."""

    rows: list[ft.Control] = []
    for event in events:
        description = event.new_value or event.reason or "Evento registrado"
        if "; regra=" in description:
            description = description.split("; regra=", maxsplit=1)[0]
        rows.append(
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=14,
                padding=15,
                on_click=lambda _event, test_id=event.test_id: on_select(test_id),
                content=ft.ResponsiveRow(
                    spacing=14,
                    run_spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            col={"xs": 12, "md": 8, "lg": 9},
                            content=ft.Row(
                                spacing=14,
                                controls=[
                                    ft.Container(
                                        width=38,
                                        height=38,
                                        border_radius=12,
                                        bgcolor=AppColors.PRIMARY_LIGHT,
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Icon(
                                            ft.Icons.HISTORY,
                                            color=AppColors.PRIMARY,
                                            size=20,
                                        ),
                                    ),
                                    ft.Column(
                                        expand=True,
                                        spacing=2,
                                        controls=[
                                            ft.Text(
                                                event.action,
                                                weight=ft.FontWeight.BOLD,
                                                color=AppColors.TEXT_PRIMARY,
                                            ),
                                            ft.Text(
                                                description,
                                                size=12,
                                                color=AppColors.TEXT_SECONDARY,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            col={"xs": 12, "md": 4, "lg": 3},
                            content=ft.Column(
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                                spacing=2,
                                controls=[
                                    ft.Text(
                                        f"{event.client} / {event.process_number}",
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        f"Ensaio #{event.test_id}",
                                        size=11,
                                        color=AppColors.TEXT_SECONDARY,
                                    ),
                                    ft.Text(
                                        f"{format_datetime(event.occurred_at)} • {event.actor}",
                                        size=10,
                                        color=AppColors.TEXT_SECONDARY,
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            )
        )
    if not rows:
        rows.append(
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=14,
                padding=28,
                content=ft.Text("Nenhum evento registrado.", color=AppColors.TEXT_SECONDARY),
            )
        )
    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=18,
        controls=[
            ft.Column(
                spacing=3,
                controls=[
                    ft.Text(
                        "Registro de atividades",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "Ações importantes registradas em todos os ensaios. "
                        "O histórico dos ensaios concluídos permanece na tela Ensaios.",
                        size=14,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                ],
            ),
            ft.Container(
                bgcolor=AppColors.INFO_LIGHT,
                border_radius=12,
                padding=14,
                content=ft.Text(
                    "Cada ação exibe o nome e o usuário autenticado responsável. "
                    "Registros importados de versões anteriores permanecem como "
                    "“Não identificado” para preservar a informação original.",
                    size=12,
                    color=AppColors.TEXT_PRIMARY,
                ),
            ),
            *rows,
        ],
    )
