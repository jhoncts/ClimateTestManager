"""Proteções de navegação e animações leves da v0.8.6.

A moldura continua persistente. A transição atua somente na opacidade da área
central e usa um token para impedir animações concorrentes. A barra lateral muda
largura primeiro e só recompõe seu conteúdo ao final, reduzindo repaints pesados
no WebView2.
"""

from __future__ import annotations

import asyncio
import traceback
from contextlib import suppress
from datetime import datetime

import flet as ft

from climatetest_manager import production_app, v084_stability
from climatetest_manager.config import get_database_path

_TRANSITION_MS = 90
_TRANSITION_PRIME_SECONDS = 0.012


def _log_navigation_failure(view_name: str, error: BaseException) -> None:
    """Registra falha sem permitir que uma exceção de UI derrube a sessão inteira."""

    try:
        database_path = get_database_path()
        root = database_path.parent.parent
        log_directory = root / "Logs"
        log_directory.mkdir(parents=True, exist_ok=True)
        target = log_directory / "navigation-v086.log"
        with target.open("a", encoding="utf-8") as stream:
            stream.write(
                f"[{datetime.now().isoformat(timespec='seconds')}] view={view_name}\n"
                f"{type(error).__name__}: {error}\n{traceback.format_exc()}\n"
            )
    except OSError:
        return


async def _animate_content_host(app, host: ft.Container, token: int) -> None:
    """Aplica um fade mínimo e cancela visualmente transições antigas."""

    try:
        if token != getattr(app, "_v086_transition_token", 0):
            return
        host.animate_offset = None
        host.offset = ft.Offset(0, 0)
        host.animate_opacity = None
        host.opacity = 0.985
        host.update()
        await asyncio.sleep(_TRANSITION_PRIME_SECONDS)
        if token != getattr(app, "_v086_transition_token", 0):
            return
        host.animate_opacity = ft.Animation(
            _TRANSITION_MS,
            ft.AnimationCurve.EASE_OUT_CUBIC,
        )
        host.opacity = 1
        host.update()
    except RuntimeError:
        return


async def _smooth_sidebar(app: production_app.ProductionClimateTestApplication) -> None:
    """Anima somente largura e recompõe a navegação uma vez ao final."""

    if getattr(app, "_v085_sidebar_animating", False) or app._layout.mode == "compact":
        return
    shell = getattr(app, "_v084_shell", None)
    if not isinstance(shell, ft.Row) or not shell.controls:
        return
    sidebar = shell.controls[0]
    if not isinstance(sidebar, ft.Container):
        return

    app._v085_sidebar_animating = True
    duration = max(float(v084_stability.SIDEBAR_ANIMATION_SECONDS), 0.08)
    try:
        sidebar.clip_behavior = ft.ClipBehavior.HARD_EDGE
        sidebar.animate = ft.Animation(
            int(duration * 1000),
            ft.AnimationCurve.EASE_OUT_CUBIC,
        )

        if not app._sidebar_collapsed:
            sidebar.width = 84
            with suppress(RuntimeError):
                sidebar.update()
            await asyncio.sleep(duration)
            app._sidebar_collapsed = True
            v084_stability._replace_shell_frame(app)
            return

        # Expande primeiro a superfície compacta; textos e conta são recompostos
        # somente no final, evitando a travada causada por reconstrução no meio.
        sidebar.width = app._layout.sidebar_width
        with suppress(RuntimeError):
            sidebar.update()
        await asyncio.sleep(duration)
        app._sidebar_collapsed = False
        v084_stability._replace_shell_frame(app)
    finally:
        app._v085_sidebar_animating = False


def _guard_navigation(view_name: str, method):
    def guarded(self, *args, **kwargs):
        if getattr(self, "_v086_navigation_busy", False):
            return None
        # Evita que uma troca de tela dispute um mesmo frame com a recomposição
        # final da barra lateral. A animação dura cerca de 140 ms.
        if getattr(self, "_v085_sidebar_animating", False):
            return None
        self._v086_navigation_busy = True
        try:
            return method(self, *args, **kwargs)
        except Exception as error:
            _log_navigation_failure(view_name, error)
            with suppress(Exception):
                self._show_message(
                    "A tela não pôde ser aberta. A sessão foi preservada e a falha foi registrada.",
                    error=True,
                )
            return None
        finally:
            self._v086_navigation_busy = False

    return guarded


def _animated_toggle_sidebar(self: production_app.ProductionClimateTestApplication) -> None:
    if self._layout.mode == "compact" or getattr(self, "_v085_sidebar_animating", False):
        return
    self._page.run_task(_smooth_sidebar, self)


def install() -> None:
    if getattr(production_app, "_v086_navigation_installed", False):
        return
    app = production_app.ProductionClimateTestApplication

    current_render = app._render

    def render_with_transition(self, content, *, selected_view: str) -> None:
        previous_view = getattr(self, "_selected_view", None)
        current_render(self, content, selected_view=selected_view)
        if previous_view == selected_view:
            return
        self._v086_transition_token = getattr(self, "_v086_transition_token", 0) + 1
        token = self._v086_transition_token
        host = getattr(self, "_v084_content_host", None)
        if isinstance(host, ft.Container):
            self._page.run_task(_animate_content_host, self, host, token)

    app._render = render_with_transition
    app._toggle_sidebar = _animated_toggle_sidebar

    for name in (
        "show_dashboard",
        "show_tests",
        "show_new_test",
        "show_agenda",
        "show_history",
        "show_notifications",
        "show_help",
        "show_settings",
        "show_users",
        "show_details",
        "show_edit_test",
    ):
        method = getattr(app, name, None)
        if callable(method):
            setattr(app, name, _guard_navigation(name, method))

    production_app._v086_navigation_installed = True
