"""Polimento de interação aplicado de forma consistente em toda a interface."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress

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


def apply_interaction_polish(control: ft.Control) -> ft.Control:
    """Aplica cursor de clique e estados visuais sem reescrever cada tela.

    O Flet já fornece estados Material para os botões. Aqui nós apenas garantimos uma
    linguagem consistente para mouse/hover e propagamos isso pelos controles compostos.
    """

    if isinstance(control, _CLICKABLE_TYPES) and hasattr(control, "mouse_cursor"):
        with suppress(Exception):
            control.mouse_cursor = ft.MouseCursor.CLICK

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
) -> ft.Container:
    """Item lateral nítido e estável, sem escalar texto ou ícones durante o hover."""

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
        visible=not compact,
        no_wrap=True,
    )
    icon_control = ft.Icon(icon, size=icon_size, color=selected_color)
    surface = ft.Container(
        height=46,
        border_radius=12,
        bgcolor=nav_selected if selected else None,
        padding=ft.Padding.symmetric(horizontal=12 if not compact else 8, vertical=8),
        alignment=ft.Alignment.CENTER if compact else ft.Alignment.CENTER_LEFT,
        tooltip=label if compact else None,
        animate=ft.Animation(120, ft.AnimationCurve.EASE_OUT_CUBIC),
        on_click=(lambda _event: on_click()) if on_click else None,
        badge=(
            ft.Badge(
                label=str(min(badge_count, 99)),
                bgcolor=AppColors.DANGER,
                text_color=AppColors.WHITE,
            )
            if badge_count
            else None
        ),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER if compact else ft.MainAxisAlignment.START,
            spacing=0 if compact else 11,
            controls=[icon_control, label_control],
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
        surface.on_hover = on_hover
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
    """Simula um material translúcido discreto para cartões de apoio.

    Não tenta reproduzir blur real do compositor do Windows. A intenção é manter o efeito
    visual leve e previsível em estações com hardware diferente.
    """

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
