"""Central interna de avisos operacionais e administrativos."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from climatetest_manager.repositories.climate_tests import UserNotificationSummary
from climatetest_manager.ui.formatters import format_datetime
from climatetest_manager.ui.interaction import apply_interaction_polish
from climatetest_manager.ui.theme import AppColors

NotificationKey = tuple[str, int]


def _notification_card(
    notification: UserNotificationSummary,
    *,
    checkbox: ft.Checkbox,
    on_mark_read: Callable[[str, int], None],
    on_dismiss: Callable[[str, int], None] | None,
) -> ft.Container:
    """Card compacto, selecionável e estável em sessões Flet remotas."""

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
    title_controls: list[ft.Control] = [
        ft.Text(
            notification.title,
            size=13,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
            no_wrap=False,
        )
    ]
    if not notification.is_read:
        title_controls.append(
            ft.Container(
                width=8,
                height=8,
                border_radius=4,
                bgcolor=accent,
                tooltip="Não lida",
            )
        )

    action_controls: list[ft.Control] = []
    if not notification.is_read:
        action_controls.append(
            ft.IconButton(
                icon=ft.Icons.DONE,
                icon_size=18,
                tooltip="Marcar como lida",
                on_click=lambda _event: on_mark_read(
                    notification.source_kind,
                    notification.source_id,
                ),
            )
        )
    if on_dismiss is not None:
        action_controls.append(
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_size=18,
                tooltip="Remover da minha central",
                on_click=lambda _event: on_dismiss(
                    notification.source_kind,
                    notification.source_id,
                ),
            )
        )

    card = ft.Container(
        border_radius=14,
        bgcolor=AppColors.SURFACE,
        border=ft.Border.all(
            1.5 if not notification.is_read else 1,
            accent if not notification.is_read else AppColors.DIVIDER,
        ),
        padding=14,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                checkbox,
                ft.Container(
                    width=38,
                    height=38,
                    border_radius=11,
                    bgcolor=AppColors.DANGER_LIGHT if critical else AppColors.INFO_LIGHT,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, color=accent, size=20),
                ),
                ft.Column(
                    expand=True,
                    spacing=5,
                    controls=[
                        ft.Row(spacing=7, wrap=True, controls=title_controls),
                        ft.Text(
                            notification.message,
                            size=11,
                            color=AppColors.TEXT_SECONDARY,
                            no_wrap=False,
                        ),
                        ft.Text(
                            format_datetime(notification.created_at),
                            size=9,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
                ft.Row(spacing=1, controls=action_controls),
            ],
        ),
    )
    return apply_interaction_polish(card)  # type: ignore[return-value]


def build_notifications_view(
    notifications: list[UserNotificationSummary],
    *,
    is_admin: bool,
    on_mark_read: Callable[[str, int], None],
    on_mark_all_read: Callable[[], None],
    on_mark_many_read: Callable[[list[NotificationKey]], None] | None = None,
    on_dismiss: Callable[[str, int], None] | None = None,
    on_dismiss_many: Callable[[list[NotificationKey]], None] | None = None,
) -> ft.Column:
    """Monta uma central com ações em lote sem apagar o evento técnico original."""

    unread = sum(not notification.is_read for notification in notifications)
    selected: set[NotificationKey] = set()
    mark_selected = ft.Button(
        content="Marcar selecionadas como lidas",
        icon=ft.Icons.DONE_ALL,
        disabled=True,
    )
    delete_selected = ft.Button(
        content="Remover selecionadas",
        icon=ft.Icons.DELETE_SWEEP_OUTLINED,
        color=AppColors.DANGER,
        disabled=True,
    )
    selection_text = ft.Text("Nenhuma selecionada", size=10, color=AppColors.TEXT_SECONDARY)

    def refresh_selection() -> None:
        count = len(selected)
        selection_text.value = (
            "Nenhuma selecionada" if count == 0 else f"{count} selecionada(s)"
        )
        mark_selected.disabled = count == 0 or on_mark_many_read is None
        delete_selected.disabled = count == 0 or on_dismiss_many is None
        try:
            mark_selected.page.update(mark_selected, delete_selected, selection_text)
        except RuntimeError:
            pass

    cards: list[ft.Control] = []
    for notification in notifications:
        key = (notification.source_kind, notification.source_id)
        checkbox = ft.Checkbox(value=False, tooltip="Selecionar")

        def select_item(_event: object | None = None, *, item_key=key, item=checkbox) -> None:
            if item.value:
                selected.add(item_key)
            else:
                selected.discard(item_key)
            refresh_selection()

        checkbox.on_change = select_item
        cards.append(
            _notification_card(
                notification,
                checkbox=checkbox,
                on_mark_read=on_mark_read,
                on_dismiss=on_dismiss,
            )
        )

    if not notifications:
        cards = [
            ft.Container(
                border_radius=16,
                bgcolor=AppColors.SURFACE,
                border=ft.Border.all(1, AppColors.DIVIDER),
                padding=28,
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6,
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

    def mark_selected_click(_event: object | None = None) -> None:
        if on_mark_many_read is not None and selected:
            on_mark_many_read(list(selected))

    def delete_selected_click(_event: object | None = None) -> None:
        if on_dismiss_many is not None and selected:
            on_dismiss_many(list(selected))

    mark_selected.on_click = mark_selected_click
    delete_selected.on_click = delete_selected_click

    root = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=13,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                wrap=True,
                run_spacing=8,
                controls=[
                    ft.Column(
                        spacing=2,
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
                                size=11,
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
                padding=11,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    wrap=True,
                    run_spacing=7,
                    controls=[
                        ft.Text(
                            f"{unread} não lida(s) • {len(notifications)} no histórico recente",
                            size=10,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                        selection_text,
                    ],
                ),
            ),
            *(
                [
                    ft.Row(
                        spacing=8,
                        wrap=True,
                        run_spacing=6,
                        controls=[mark_selected, delete_selected],
                    )
                ]
                if notifications
                else []
            ),
            *cards,
        ],
    )
    return apply_interaction_polish(root)  # type: ignore[return-value]
