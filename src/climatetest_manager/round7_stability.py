"""Movimento e guardas de atualização da experiência R7."""

from __future__ import annotations

import asyncio
from contextlib import suppress

import flet as ft

from climatetest_manager import production_app
from climatetest_manager.round7_runtime import CleanNewTestView

_original_init = CleanNewTestView.__init__
_original_mode_change = CleanNewTestView._on_mode_change


def _init(self, *args, **kwargs) -> None:
    _original_init(self, *args, **kwargs)
    if self._table17_guide not in self._refresh_targets:
        self._refresh_targets = (*self._refresh_targets, self._table17_guide)


def _mode_change(self, event: object | None = None) -> None:
    _original_mode_change(self, event)
    with suppress(RuntimeError):
        self._table17_guide.update()


async def _animate_sidebar(app) -> None:
    if getattr(app, "_r7_sidebar_animating", False) or app._layout.mode == "compact":
        return
    app._r7_sidebar_animating = True
    try:
        shell = getattr(app._screen_container, "content", None)
        controls = getattr(shell, "controls", None)
        sidebar = controls[0] if isinstance(controls, list) and controls else None
        if isinstance(sidebar, ft.Container):
            target = 84 if not app._sidebar_collapsed else app._layout.sidebar_width
            sidebar.clip_behavior = ft.ClipBehavior.HARD_EDGE
            sidebar.animate = ft.Animation(180, ft.AnimationCurve.EASE_OUT_CUBIC)
            sidebar.width = target
            with suppress(RuntimeError):
                sidebar.update()
            await asyncio.sleep(0.18)
        app._sidebar_collapsed = not app._sidebar_collapsed
        if app._screen_container is not None and app._current_content is not None:
            app._screen_container.content = app._build_current_shell()
            with suppress(RuntimeError):
                app._screen_container.update()
            app._restore_scroll_position()
    finally:
        app._r7_sidebar_animating = False


def _toggle_sidebar(self) -> None:
    if self._layout.mode != "compact":
        self._page.run_task(_animate_sidebar, self)


def install() -> None:
    CleanNewTestView.__init__ = _init
    CleanNewTestView._on_mode_change = _mode_change
    production_app.ProductionClimateTestApplication._toggle_sidebar = _toggle_sidebar
