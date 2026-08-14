"""Moldura de navegação usada pela edição de produção."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from climatetest_manager import __build_revision__, __version__
from climatetest_manager.services.auth import UserSummary
from climatetest_manager.ui.components import github_credit, user_avatar
from climatetest_manager.ui.interaction import (
    apply_interaction_polish,
    hoverable_navigation_surface,
)
from climatetest_manager.ui.responsive import LayoutProfile
from climatetest_manager.ui.theme import AppColors


def build_production_shell(
    content: ft.Control,
    *,
    selected_view: str,
    on_dashboard: Callable[[], None],
    on_tests: Callable[[], None],
    on_new_test: Callable[[], None] | None,
    on_agenda: Callable[[], None],
    on_history: Callable[[], None],
    on_notifications: Callable[[], None],
    on_help: Callable[[], None],
    on_settings: Callable[[], None],
    on_users: Callable[[], None] | None,
    on_logout: Callable[[], None],
    on_github: Callable[[], None],
    on_toggle_sidebar: Callable[[], None] | None,
    current_user: UserSummary,
    layout: LayoutProfile,
    notification_count: int,
) -> ft.Row:
    compact = layout.compact_navigation
    brand_icon = ft.Container(
        width=layout.brand_icon_size,
        height=layout.brand_icon_size,
        border_radius=12,
        bgcolor=AppColors.SURFACE,
        border=ft.Border.all(1, AppColors.GLASS_BORDER),
        padding=1,
        alignment=ft.Alignment.CENTER,
        content=ft.Image(
            src="brand/climatetest-logo-ui.png",
            fit=ft.BoxFit.CONTAIN,
            filter_quality=ft.FilterQuality.HIGH,
            anti_alias=True,
        ),
    )
    if compact:
        brand: ft.Control = ft.Column(
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                brand_icon,
                ft.IconButton(
                    icon=ft.Icons.KEYBOARD_DOUBLE_ARROW_RIGHT,
                    tooltip="Expandir menu lateral",
                    icon_size=19,
                    on_click=(lambda _event: on_toggle_sidebar()) if on_toggle_sidebar else None,
                ),
            ],
        )
    else:
        brand = ft.Row(
            spacing=10,
            controls=[
                brand_icon,
                ft.Column(
                    spacing=0,
                    controls=[
                        ft.Text(
                            "ClimateTest",
                            size=17,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                        ft.Text("Manager", size=11, color=AppColors.TEXT_SECONDARY),
                    ],
                ),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.KEYBOARD_DOUBLE_ARROW_LEFT,
                    tooltip="Recolher menu lateral",
                    icon_size=19,
                    on_click=(lambda _event: on_toggle_sidebar()) if on_toggle_sidebar else None,
                ),
            ],
        )

    navigation = [
        ("Dashboard", ft.Icons.DASHBOARD_OUTLINED, "dashboard", on_dashboard, 0),
        ("Ensaios", ft.Icons.LIST_ALT_OUTLINED, "tests", on_tests, 0),
    ]
    if on_new_test is not None:
        navigation.append(("Novo ensaio", ft.Icons.ADD_CIRCLE_OUTLINE, "new_test", on_new_test, 0))
    navigation.extend(
        [
            ("Agenda", ft.Icons.CALENDAR_MONTH_OUTLINED, "agenda", on_agenda, 0),
            ("Atividades", ft.Icons.HISTORY, "history", on_history, 0),
            (
                "Notificações",
                ft.Icons.NOTIFICATIONS_OUTLINED,
                "notifications",
                on_notifications,
                notification_count,
            ),
            ("Guia de uso", ft.Icons.HELP_OUTLINE, "help", on_help, 0),
            ("Configurações", ft.Icons.SETTINGS_OUTLINED, "settings", on_settings, 0),
        ]
    )
    if on_users is not None:
        navigation.append(("Usuários", ft.Icons.GROUPS_OUTLINED, "users", on_users, 0))

    nav_controls: list[ft.Control] = []
    for label, icon, view, callback, badge in navigation:
        selected = selected_view == view or (view == "tests" and selected_view == "details")
        nav_controls.append(
            hoverable_navigation_surface(
                label=label,
                icon=icon,
                selected=selected,
                compact=compact,
                icon_size=layout.navigation_icon_size,
                on_click=callback,
                badge_count=badge,
            )
        )

    account = (
        ft.Column(
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    tooltip=f"{current_user.full_name} • {current_user.role_label}",
                    content=user_avatar(current_user, size=34),
                ),
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    tooltip="Sair da conta",
                    icon_size=18,
                    on_click=lambda _event: on_logout(),
                ),
            ],
        )
        if compact
        else ft.Row(
            spacing=8,
            controls=[
                user_avatar(current_user, size=34),
                ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[
                        ft.Text(
                            current_user.full_name,
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                            no_wrap=True,
                        ),
                        ft.Text(
                            current_user.role_label,
                            size=9,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    tooltip="Sair da conta",
                    icon_size=18,
                    on_click=lambda _event: on_logout(),
                ),
            ],
        )
    )

    footer = (
        ft.Column(
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                github_credit(lambda _event: on_github(), compact=True),
            ],
        )
        if compact
        else ft.Column(
            spacing=2,
            controls=[
                ft.Text(
                    f"IEC 60079-0 • v{__version__}",
                    size=9,
                    color=AppColors.TEXT_SECONDARY,
                    no_wrap=True,
                    tooltip=f"Revisão instalada: {__build_revision__}",
                ),
                ft.Text(
                    __build_revision__,
                    size=8,
                    color=AppColors.TEXT_SECONDARY,
                    no_wrap=True,
                ),
                github_credit(lambda _event: on_github()),
            ],
        )
    )

    sidebar = ft.Container(
        width=layout.sidebar_width,
        bgcolor=AppColors.NAV_BACKGROUND,
        padding=ft.Padding.all(layout.sidebar_padding),
        content=ft.Column(
            spacing=8,
            horizontal_alignment=(
                ft.CrossAxisAlignment.CENTER if compact else ft.CrossAxisAlignment.STRETCH
            ),
            controls=[
                brand,
                ft.Container(height=8),
                ft.Column(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=nav_controls,
                ),
                ft.Divider(height=1, color=AppColors.DIVIDER),
                account,
                footer,
            ],
        ),
    )
    shell = ft.Row(
        expand=True,
        spacing=0,
        controls=[
            sidebar,
            ft.Container(
                expand=True,
                bgcolor=AppColors.PAGE_BACKGROUND,
                padding=layout.content_padding,
                content=content,
            ),
        ],
    )
    return apply_interaction_polish(shell)  # type: ignore[return-value]
