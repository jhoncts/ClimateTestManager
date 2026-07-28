"""Configurações operacionais disponíveis antes do futuro módulo de login."""

from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

from climatetest_manager.repositories.climate_tests import NotificationStatus
from climatetest_manager.ui.formatters import format_datetime
from climatetest_manager.ui.theme import AppColors


def build_settings_view(
    *,
    database_path: Path,
    notifications_enabled: bool,
    notification_status: NotificationStatus,
    theme_mode: str,
    on_theme_change: Callable[[str], None],
    on_enable_notifications: Callable[[], None],
    on_disable_notifications: Callable[[], None],
    on_test_notification: Callable[[], None],
    on_open_data_folder: Callable[[], None],
    on_backup: Callable[[object | None], Awaitable[None]],
) -> ft.Column:
    """Monta opções locais sem antecipar preferências dependentes de usuário."""

    status_color = AppColors.PRIMARY if notifications_enabled else AppColors.WARNING
    status_text = "Ativo" if notifications_enabled else "Inativo"
    if notification_status.last_checked_at is None:
        last_result = "O agente ainda não registrou nenhuma verificação."
    elif notification_status.failed_count:
        last_result = (
            f"Última verificação: {notification_status.failed_count} falha(s). "
            f"{notification_status.last_error or ''}"
        ).strip()
    elif notification_status.delivered_count:
        last_result = (
            f"Última verificação: {notification_status.delivered_count} aviso(s) enviado(s)."
        )
    else:
        last_result = "Última verificação concluída, sem avisos pendentes."
    theme_switch = ft.Switch(
        label="Usar tema escuro",
        value=theme_mode == "dark",
    )
    theme_switch.on_change = lambda _event: on_theme_change(
        "dark" if theme_switch.value else "light"
    )
    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=20,
        controls=[
            ft.Column(
                spacing=3,
                controls=[
                    ft.Text(
                        "Configurações",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "Preferências locais e recursos executados pelo Windows.",
                        size=14,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                ],
            ),
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=16,
                padding=22,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=3,
                            controls=[
                                ft.Text(
                                    "Aparência",
                                    size=17,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    "A escolha fica salva neste computador.",
                                    size=12,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                        theme_switch,
                    ],
                ),
            ),
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=16,
                padding=22,
                content=ft.Column(
                    spacing=14,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column(
                                    spacing=3,
                                    controls=[
                                        ft.Text(
                                            "Avisos em segundo plano",
                                            size=17,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            "Verifica prazos a cada 5 minutos, mesmo com a janela "
                                            "principal fechada.",
                                            size=12,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                ),
                                ft.Container(
                                    border_radius=18,
                                    bgcolor=(
                                        AppColors.PRIMARY_LIGHT
                                        if notifications_enabled
                                        else AppColors.WARNING_LIGHT
                                    ),
                                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                                    content=ft.Text(
                                        status_text,
                                        weight=ft.FontWeight.BOLD,
                                        color=status_color,
                                    ),
                                ),
                            ],
                        ),
                        ft.Text(
                            f"Banco monitorado: {database_path}",
                            size=12,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        ft.Text(
                            "Última verificação: "
                            f"{format_datetime(notification_status.last_checked_at)}",
                            size=12,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        ft.Text(last_result, size=12, color=AppColors.TEXT_SECONDARY),
                        ft.Text(
                            "O computador precisa estar ligado e a sessão do Windows iniciada. "
                            "A tarefa chama diretamente o notificador sem abrir CMD ou PowerShell.",
                            size=12,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        ft.Row(
                            controls=[
                                ft.Button(
                                    content="Testar notificação",
                                    icon=ft.Icons.NOTIFICATIONS,
                                    on_click=lambda _event: on_test_notification(),
                                ),
                                ft.Button(
                                    content="Ativar avisos",
                                    icon=ft.Icons.NOTIFICATIONS_ACTIVE,
                                    disabled=notifications_enabled,
                                    bgcolor=AppColors.PRIMARY,
                                    color=AppColors.WHITE,
                                    on_click=lambda _event: on_enable_notifications(),
                                ),
                                ft.Button(
                                    content="Desativar avisos",
                                    icon=ft.Icons.NOTIFICATIONS_OFF,
                                    disabled=not notifications_enabled,
                                    on_click=lambda _event: on_disable_notifications(),
                                ),
                            ]
                        ),
                    ],
                ),
            ),
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=16,
                padding=22,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(
                                    "Local dos dados",
                                    size=17,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Container(
                                    border_radius=18,
                                    bgcolor=AppColors.PRIMARY_LIGHT,
                                    padding=ft.Padding.symmetric(
                                        horizontal=12,
                                        vertical=6,
                                    ),
                                    content=ft.Text(
                                        "Conectado",
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.PRIMARY,
                                    ),
                                ),
                            ],
                        ),
                        ft.Text(
                            "Arquivo em uso pelo programa",
                            size=11,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        ft.Text(str(database_path), size=12, color=AppColors.TEXT_PRIMARY),
                        ft.Text(
                            "Todos os ensaios e atividades são lidos e salvos neste arquivo. "
                            "Mantenha-o em disco local; o OneDrive pode receber a cópia de "
                            "segurança gerada pelo botão abaixo.",
                            size=12,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        ft.Row(
                            controls=[
                                ft.Button(
                                    content="Abrir pasta",
                                    icon=ft.Icons.FOLDER_OPEN,
                                    on_click=lambda _event: on_open_data_folder(),
                                ),
                                ft.Button(
                                    content="Criar cópia de segurança",
                                    icon=ft.Icons.BACKUP,
                                    on_click=on_backup,
                                ),
                            ]
                        ),
                    ],
                ),
            ),
            ft.Container(
                bgcolor=AppColors.INFO_LIGHT,
                border_radius=12,
                padding=14,
                content=ft.Text(
                    "A Agenda interna reúne as datas de retirada dos ensaios ativos. Cada "
                    "ensaio também pode gerar um arquivo .ics. Integração automática com "
                    "calendário e e-mail ficará para o futuro login e autorização segura.",
                    size=12,
                    color=AppColors.TEXT_PRIMARY,
                ),
            ),
        ],
    )
