"""Central interna de avisos operacionais e administrativos."""

from collections.abc import Callable

import flet as ft

from climatetest_manager.repositories.climate_tests import UserNotificationSummary
from climatetest_manager.ui.formatters import format_datetime
from climatetest_manager.ui.theme import AppColors


def _notification_card(
    notification: UserNotificationSummary,
    *,
    on_mark_read: Callable[[str, int], None],
) -> ft.Container:
    critical = notification.severity in {
        "critical",
        "crítica",
        "critico",
        "crítico",
        "high",
        "alta",
    }
    accent = AppColors.DANGER if critical else AppColors.INFO
    return ft.Container(
        border_radius=14,
        bgcolor=AppColors.SURFACE,
        border=ft.Border.all(
            1.5 if not notification.is_read else 1,
            accent if not notification.is_read else AppColors.DIVIDER,
        ),
        padding=16,
        on_click=(
            (lambda _event: on_mark_read(notification.source_kind, notification.source_id))
            if not notification.is_read
            else None
        ),
        content=ft.Row(
            spacing=13,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(
                    width=42,
                    height=42,
                    border_radius=12,
                    bgcolor=AppColors.DANGER_LIGHT if critical else AppColors.INFO_LIGHT,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(
                        ft.Icons.REPORT_PROBLEM_OUTLINED
                        if notification.source_kind == "incident"
                        else ft.Icons.SCHEDULE_OUTLINED,
                        color=accent,
                        size=22,
                    ),
                ),
                ft.Column(
                    expand=True,
                    spacing=5,
                    controls=[
                        ft.Row(
                            wrap=True,
                            controls=[
                                ft.Text(
                                    notification.title,
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                    expand=True,
                                ),
                                *(
                                    [
                                        ft.Container(
                                            width=8,
                                            height=8,
                                            border_radius=4,
                                            bgcolor=accent,
                                            tooltip="Não lida",
                                        )
                                    ]
                                    if not notification.is_read
                                    else []
                                ),
                            ],
                        ),
                        ft.Text(
                            notification.message,
                            size=12,
                            color=AppColors.TEXT_SECONDARY,
                            selectable=True,
                        ),
                        ft.Text(
                            format_datetime(notification.created_at),
                            size=10,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
            ],
        ),
    )


def build_notifications_view(
    notifications: list[UserNotificationSummary],
    *,
    is_admin: bool,
    on_mark_read: Callable[[str, int], None],
    on_mark_all_read: Callable[[], None],
) -> ft.Column:
    unread = sum(not notification.is_read for notification in notifications)
    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                wrap=True,
                controls=[
                    ft.Column(
                        spacing=3,
                        controls=[
                            ft.Text(
                                "Notificações",
                                size=25,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            ft.Text(
                                (
                                    "Prazos operacionais e falhas restritas à administração."
                                    if is_admin
                                    else "Prazos e avisos operacionais do laboratório."
                                ),
                                size=12,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                    ft.Button(
                        content="Marcar todas como lidas",
                        icon=ft.Icons.DONE_ALL,
                        disabled=unread == 0,
                        on_click=lambda _event: on_mark_all_read(),
                    ),
                ],
            ),
            ft.Container(
                border_radius=12,
                bgcolor=AppColors.INFO_LIGHT,
                padding=13,
                content=ft.Text(
                    f"{unread} não lida(s) • {len(notifications)} aviso(s) no histórico recente",
                    size=11,
                    color=AppColors.TEXT_PRIMARY,
                ),
            ),
            *(
                [
                    _notification_card(notification, on_mark_read=on_mark_read)
                    for notification in notifications
                ]
                if notifications
                else [
                    ft.Container(
                        border_radius=16,
                        bgcolor=AppColors.SURFACE,
                        padding=28,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(
                                    ft.Icons.NOTIFICATIONS_NONE,
                                    size=34,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                                ft.Text("Nenhuma notificação disponível."),
                            ],
                        ),
                    )
                ]
            ),
        ],
    )
