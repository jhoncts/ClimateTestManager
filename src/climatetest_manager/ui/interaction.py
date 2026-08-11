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

    if isinstance(control, _CLICKABLE_TYPES):
        if hasattr(control, "mouse_cursor"):
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
    """Cria um item de menu com resposta suave ao mouse e sem poluição visual."""

    base_bg = AppColors.NAV_SELECTED if selected else AppColors.NAV_BACKGROUND
    selected_color = AppColors.PRIMARY if selected else AppColors.NAV_TEXT
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
        bgcolor=base_bg,
        padding=ft.Padding.symmetric(horizontal=12 if not compact else 8, vertical=8),
        alignment=ft.Alignment.CENTER if compact else ft.Alignment.CENTER_LEFT,
        tooltip=label if compact else None,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT_CUBIC),
        animate_scale=ft.Animation(130, ft.AnimationCurve.EASE_OUT),
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
        if selected:
            surface.bgcolor = AppColors.NAV_SELECTED
            surface.scale = 1.01 if event.data == "true" else 1.0
        elif event.data == "true":
            surface.bgcolor = AppColors.NAV_HOVER
            surface.scale = 1.012
            icon_control.color = AppColors.PRIMARY
            label_control.color = AppColors.TEXT_PRIMARY
        else:
            surface.bgcolor = AppColors.NAV_BACKGROUND
            surface.scale = 1.0
            icon_control.color = AppColors.NAV_TEXT
            label_control.color = AppColors.NAV_TEXT
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
