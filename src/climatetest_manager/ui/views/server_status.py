"""Resumo visível da infraestrutura central usada pelas estações."""

from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

from climatetest_manager.services.network import ServerIdentity
from climatetest_manager.ui.theme import AppColors


def build_server_status_card(
    identity: ServerIdentity,
    *,
    backup_directory: Path | None,
    is_admin: bool,
    on_configure_backup: Callable[[object | None], Awaitable[None]] | None = None,
) -> ft.Container:
    """Mostra os endereços que o usuário pode usar e o estado da cópia externa."""

    address_lines = [f"{address}:{identity.port}" for address in identity.addresses]
    if not address_lines:
        address_lines = ["Nenhum IPv4 da rede foi identificado neste momento."]

    backup_configured = backup_directory is not None
    backup_action: list[ft.Control] = []
    if is_admin and on_configure_backup is not None:
        backup_action.append(
            ft.Button(
                content=(
                    "Alterar cópia externa"
                    if backup_configured
                    else "Configurar cópia externa"
                ),
                icon=ft.Icons.BACKUP_OUTLINED,
                on_click=on_configure_backup,
            )
        )

    return ft.Container(
        bgcolor=AppColors.SURFACE,
        border_radius=18,
        padding=22,
        border=ft.Border.all(1, AppColors.DIVIDER),
        content=ft.Column(
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    wrap=True,
                    run_spacing=8,
                    controls=[
                        ft.Column(
                            spacing=3,
                            controls=[
                                ft.Text(
                                    "Servidor central",
                                    size=17,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    "Informações para instalar ou diagnosticar uma estação de trabalho.",
                                    size=12,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                        ft.Container(
                            border_radius=18,
                            bgcolor=AppColors.PRIMARY_LIGHT,
                            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                            content=ft.Text(
                                "ATIVO NA REDE",
                                size=10,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.PRIMARY,
                            ),
                        ),
                    ],
                ),
                ft.ResponsiveRow(
                    spacing=12,
                    run_spacing=10,
                    controls=[
                        ft.Container(
                            col={"xs": 12, "md": 6},
                            border_radius=12,
                            bgcolor=AppColors.PAGE_BACKGROUND,
                            padding=14,
                            content=ft.Column(
                                spacing=5,
                                controls=[
                                    ft.Text(
                                        "Nome do computador servidor",
                                        size=10,
                                        color=AppColors.TEXT_SECONDARY,
                                    ),
                                    ft.Text(
                                        identity.hostname,
                                        size=15,
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.TEXT_PRIMARY,
                                        selectable=True,
                                    ),
                                    ft.Text(
                                        f"{identity.hostname}:{identity.port}",
                                        size=11,
                                        color=AppColors.PRIMARY,
                                        selectable=True,
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            col={"xs": 12, "md": 6},
                            border_radius=12,
                            bgcolor=AppColors.PAGE_BACKGROUND,
                            padding=14,
                            content=ft.Column(
                                spacing=5,
                                controls=[
                                    ft.Text(
                                        "Endereço(s) IP do servidor",
                                        size=10,
                                        color=AppColors.TEXT_SECONDARY,
                                    ),
                                    ft.Text(
                                        "\n".join(address_lines),
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.TEXT_PRIMARY,
                                        selectable=True,
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
                ft.Container(
                    border_radius=12,
                    bgcolor=AppColors.INFO_LIGHT,
                    padding=12,
                    content=ft.Row(
                        spacing=9,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Icon(ft.Icons.WIFI_FIND, color=AppColors.INFO, size=19),
                            ft.Text(
                                "O instalador da estação procura este servidor automaticamente. "
                                "Se a rede bloquear a descoberta, informe o nome acima ou um dos "
                                "IPs exibidos. Não é necessário usar o CMD.",
                                expand=True,
                                size=11,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                        ],
                    ),
                ),
                ft.Divider(height=1, color=AppColors.DIVIDER),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    wrap=True,
                    run_spacing=8,
                    controls=[
                        ft.Column(
                            spacing=3,
                            controls=[
                                ft.Text(
                                    "Cópia externa automática",
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    (
                                        str(backup_directory)
                                        if backup_configured
                                        else "Ainda não configurada. Recomenda-se OneDrive ou outro destino protegido."
                                    ),
                                    size=11,
                                    color=(
                                        AppColors.TEXT_SECONDARY
                                        if backup_configured
                                        else AppColors.WARNING
                                    ),
                                    selectable=backup_configured,
                                ),
                            ],
                        ),
                        ft.Row(controls=backup_action),
                    ],
                ),
            ],
        ),
    )
