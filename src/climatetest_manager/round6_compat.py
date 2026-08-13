"""Compatibilidade estrita da R6 com os controles disponíveis no Flet 0.86.4."""

from __future__ import annotations

import flet as ft

from climatetest_manager.round4_runtime import _safe_update
from climatetest_manager.round6_runtime import apply_interaction_polish
from climatetest_manager.ui import shell as shell_module
from climatetest_manager.ui.components import dialogs as dialogs_module
from climatetest_manager.ui.theme import AppColors


def navigation_surface(
    *,
    label: str,
    icon: ft.IconData,
    selected: bool,
    compact: bool,
    icon_size: int,
    on_click,
    badge_count: int = 0,
) -> ft.Container:
    """Mantém o contador dentro do item e longe da barra de rolagem."""

    selected_color = AppColors.PRIMARY if selected else AppColors.NAV_TEXT
    label_control = ft.Text(
        label,
        size=13,
        height=1.35,
        weight=ft.FontWeight.BOLD if selected else ft.FontWeight.W_500,
        color=selected_color,
        no_wrap=True,
        max_lines=1,
    )
    icon_control = ft.Icon(icon, size=icon_size, color=selected_color)
    badge = ft.Container(
        visible=badge_count > 0,
        width=24,
        height=20,
        border_radius=10,
        bgcolor=AppColors.DANGER,
        alignment=ft.Alignment.CENTER,
        content=ft.Text(
            str(min(badge_count, 99)),
            size=9,
            weight=ft.FontWeight.BOLD,
            color=AppColors.WHITE,
            no_wrap=True,
        ),
    )
    if compact:
        row_controls: list[ft.Control] = [icon_control]
        if badge_count:
            row_controls.append(badge)
    else:
        row_controls = [icon_control, ft.Container(expand=True, content=label_control)]
        if badge_count:
            row_controls.append(badge)

    surface = ft.Container(
        height=52,
        border_radius=12,
        bgcolor=AppColors.NAV_SELECTED if selected else None,
        padding=ft.Padding.only(
            left=8 if compact else 12,
            right=8 if compact else 14,
            top=9,
            bottom=9,
        ),
        alignment=ft.Alignment.CENTER if compact else ft.Alignment.CENTER_LEFT,
        tooltip=label if compact else None,
        on_click=(lambda _event: on_click()) if on_click else None,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER if compact else ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=5 if compact else 11,
            controls=row_controls,
        ),
    )

    def on_hover(event: ft.HoverEvent) -> None:
        hovering = event.data == "true"
        if selected:
            surface.bgcolor = AppColors.NAV_SELECTED
            icon_control.color = AppColors.PRIMARY
            label_control.color = AppColors.PRIMARY
        elif hovering:
            surface.bgcolor = AppColors.NAV_HOVER
            icon_control.color = AppColors.PRIMARY
            label_control.color = AppColors.TEXT_PRIMARY
        else:
            surface.bgcolor = None
            icon_control.color = AppColors.NAV_TEXT
            label_control.color = AppColors.NAV_TEXT
        _safe_update(surface)

    if on_click is not None:
        surface.on_hover = on_hover
        surface.mouse_cursor = ft.MouseCursor.CLICK
    return surface


def install() -> None:
    shell_module.hoverable_navigation_surface = navigation_surface
    dialogs_module.apply_interaction_polish = apply_interaction_polish


install()
