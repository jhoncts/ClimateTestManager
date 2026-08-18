"""Polimento de interação aplicado de forma consistente em toda a interface."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from inspect import iscoroutinefunction

import flet as ft

from climatetest_manager.ui.theme import AppColors

_CLICKABLE_TYPES = (
    ft.Button,
    ft.TextButton,
    ft.IconButton,
    ft.Switch,
    ft.Checkbox,
    ft.Radio,
    ft.Dropdown,
)
_EVENT_NAMES = ("on_click", "on_change", "on_select", "on_hover", "on_submit")


def _activate_control_theme(control: ft.Control) -> None:
    """Restaura a paleta do dispositivo antes de qualquer callback tardio."""

    with suppress(Exception):
        page = control.page
        mode = getattr(page, "_climatetest_theme_mode", None)
        if mode:
            AppColors.apply_mode(str(mode))


def _theme_aware_handler(control: ft.Control, handler):
    if handler is None or getattr(handler, "_climatetest_theme_aware", False):
        return handler
    if iscoroutinefunction(handler):

        async def wrapped(event=None):
            _activate_control_theme(control)
            return await handler(event)

    else:

        def wrapped(event=None):
            _activate_control_theme(control)
            return handler(event)

    wrapped._climatetest_theme_aware = True
    return wrapped


def _wrap_events(control: ft.Control) -> None:
    for event_name in _EVENT_NAMES:
        with suppress(Exception):
            handler = getattr(control, event_name, None)
            if callable(handler):
                setattr(control, event_name, _theme_aware_handler(control, handler))


def _polish_button(control: ft.Control) -> None:
    with suppress(Exception):
        control.mouse_cursor = ft.MouseCursor.CLICK
    if not isinstance(control, (ft.Button, ft.TextButton, ft.IconButton)):
        return
    with suppress(Exception):
        if control.style is None:
            control.style = ft.ButtonStyle(
                overlay_color={
                    ft.ControlState.HOVERED: AppColors.INTERACTIVE_HOVER,
                    ft.ControlState.PRESSED: AppColors.INTERACTIVE_PRESSED,
                },
                elevation={
                    ft.ControlState.HOVERED: 3,
                    ft.ControlState.PRESSED: 0,
                },
            )


def apply_interaction_polish(control: ft.Control) -> ft.Control:
    """Aplica cursor, hover e contexto de tema sem transformar/reescalar texto ou ícones."""

    _wrap_events(control)
    if isinstance(control, _CLICKABLE_TYPES):
        _polish_button(control)

    if isinstance(control, ft.Switch):
        with suppress(Exception):
            control.hover_color = AppColors.INTERACTIVE_HOVER
            control.overlay_color = {
                ft.ControlState.HOVERED: AppColors.INTERACTIVE_HOVER,
                ft.ControlState.PRESSED: AppColors.INTERACTIVE_PRESSED,
            }

    if isinstance(control, ft.Container) and control.on_click is not None:
        with suppress(Exception):
            control.ink = True
            control.mouse_cursor = ft.MouseCursor.CLICK

    child = getattr(control, "content", None)
    if isinstance(child, ft.Control):
        apply_interaction_polish(child)
    children = getattr(control, "controls", None)
    if isinstance(children, list):
        for item in children:
            if isinstance(item, ft.Control):
                apply_interaction_polish(item)
    actions = getattr(control, "actions", None)
    if isinstance(actions, list):
        for item in actions:
            if isinstance(item, ft.Control):
                apply_interaction_polish(item)
    return control


def hoverable_navigation_surface(
    *,
    label: str,
    icon: ft.IconData,
    selected: bool,
    compact: bool,
    icon_size: int,
    on_click: Callable[[], None] | None,
    badge_count: int = 0,
    surface_width: int | None = None,
) -> ft.Container:
    """Item lateral com geometria explícita e previsível no WebView2 do Windows.

    A navegação antiga deixava o texto dentro de uma ``Row(tight=True)`` aninhada.
    Em algumas escalas do Windows, o cálculo intermediário recebia largura zero e
    somente o ícone era pintado. Aqui ícone, rótulo e badge são irmãos diretos e o
    rótulo recebe uma largura numérica; nenhum ``expand`` participa dessa linha.
    """

    nav_selected = AppColors.NAV_SELECTED
    nav_hover = AppColors.NAV_HOVER
    nav_text = AppColors.NAV_TEXT
    primary = AppColors.PRIMARY
    text_primary = AppColors.TEXT_PRIMARY
    selected_color = primary if selected else nav_text
    label_control = ft.Text(
        label,
        size=13,
        weight=ft.FontWeight.BOLD if selected else ft.FontWeight.W_500,
        color=selected_color,
        no_wrap=True,
        max_lines=1,
    )
    icon_control = ft.Icon(icon, size=icon_size, color=selected_color)
    badge = ft.Container(
        width=22,
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
    resolved_width = surface_width or (60 if compact else 212)
    if compact:
        icon_box: ft.Control = ft.Container(
            width=36,
            height=34,
            alignment=ft.Alignment.CENTER,
            content=icon_control,
        )
        if badge_count:
            badge.width = 18
            badge.height = 18
            badge.right = 0
            badge.top = 0
            icon_box = ft.Stack(width=40, height=36, controls=[icon_box, badge])
        row_controls: list[ft.Control] = [icon_box]
        row_alignment = ft.MainAxisAlignment.CENTER
        row_spacing = 0
    else:
        horizontal_padding = 12
        icon_width = 28
        row_spacing = 9
        badge_space = (badge.width or 22) + row_spacing if badge_count else 0
        label_width = max(
            84,
            resolved_width - (horizontal_padding * 2) - icon_width - row_spacing - badge_space,
        )
        icon_box = ft.Container(
            width=icon_width,
            height=34,
            alignment=ft.Alignment.CENTER,
            content=icon_control,
        )
        label_box = ft.Container(
            width=label_width,
            height=34,
            alignment=ft.Alignment.CENTER_LEFT,
            content=label_control,
        )
        row_controls = [icon_box, label_box]
        if badge_count:
            row_controls.append(badge)
        row_alignment = ft.MainAxisAlignment.START
    surface = ft.Container(
        width=resolved_width,
        height=52,
        border_radius=12,
        bgcolor=nav_selected if selected else None,
        padding=ft.Padding.symmetric(horizontal=12 if not compact else 8, vertical=9),
        alignment=ft.Alignment.CENTER if compact else ft.Alignment.CENTER_LEFT,
        tooltip=label if compact else None,
        on_click=(lambda _event: on_click()) if on_click else None,
        content=ft.Row(
            alignment=row_alignment,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=row_spacing,
            controls=row_controls,
        ),
    )

    def on_hover(event: ft.HoverEvent) -> None:
        hovering = event.data == "true"
        if selected:
            surface.bgcolor = nav_selected
            icon_control.color = primary
            label_control.color = primary
        elif hovering:
            surface.bgcolor = nav_hover
            icon_control.color = primary
            label_control.color = text_primary
        else:
            surface.bgcolor = None
            icon_control.color = nav_text
            label_control.color = nav_text
        with suppress(RuntimeError):
            surface.update()

    if on_click is not None:
        surface.on_hover = _theme_aware_handler(surface, on_hover)
        with suppress(Exception):
            surface.mouse_cursor = ft.MouseCursor.CLICK
    return surface


def glass_surface(
    content: ft.Control,
    *,
    padding: int = 18,
    radius: int = 18,
    accent: bool = False,
) -> ft.Container:
    """Material leve e previsível, sem blur ou transformações que reduzam nitidez."""

    return ft.Container(
        border_radius=radius,
        bgcolor=AppColors.GLASS_SURFACE_ACCENT if accent else AppColors.GLASS_SURFACE,
        border=ft.Border.all(1, AppColors.GLASS_BORDER),
        padding=padding,
        shadow=ft.BoxShadow(
            blur_radius=22,
            spread_radius=0,
            color=AppColors.SURFACE_SHADOW,
            offset=ft.Offset(0, 7),
        ),
        content=content,
    )
