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
    """Card deliberadamente simples para renderizar igual no host e em FletApp remoto."""

    critical = notification.severity in {
        "critical",
        "crítica",
        "critico",
        "crítico",
        "high",
        "alta",
    }
    accent = AppColors.DANGER if critical else AppColors.INFO
    icon = (
        ft.Icons.REPORT_PROBLEM_OUTLINED
        if notification.source_kind == "incident"
        else ft.Icons.SCHEDULE_OUTLINED
    )
    title_row_controls: list[ft.Control] = [
        ft.Text(
            notification.title,
            size=14,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )
    ]
    if not notification.is_read:
        title_row_controls.append(
            ft.Container(
                width=8,
                height=8,
                border_radius=4,
                bgcolor=accent,
                tooltip="Não lida",
            )
        )

    return ft.Container(
        width=float("inf"),
        border_radius=14,
        bgcolor=AppColors.SURFACE,
        border=ft.Border.all(
            1.5 if not notification.is_read else 1,
            accent if not notification.is_read else AppColors.DIVIDER,
        ),
        padding=16,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
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
                    content=ft.Icon(icon, color=accent, size=22),
                ),
                ft.Container(
                    expand=True,
                    content=ft.Column(
                        spacing=6,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                        controls=[
                            ft.Row(
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=title_row_controls,
                            ),
                            ft.Text(
                                notification.message,
                                size=12,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                            ft.Text(
                                format_datetime(notification.created_at),
                                size=10,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
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
    cards: list[ft.Control]
    if notifications:
        cards = [
            _notification_card(notification, on_mark_read=on_mark_read)
            for notification in notifications
        ]
    else:
        cards = [
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
                        ft.Text(
                            "Nenhuma notificação disponível.",
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
            )
        ]

    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                wrap=True,
                run_spacing=8,
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
            *cards,
        ],
    )
