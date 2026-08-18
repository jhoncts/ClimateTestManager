"""Regressão: o shell final não pode voltar à navegação legada monkeypatchada."""

import flet as ft

from climatetest_manager.services.auth import UserSummary
from climatetest_manager.ui import shell as shell_module
from climatetest_manager.ui.responsive import LayoutProfile


def _texts(control: ft.Control) -> list[str]:
    values: list[str] = []

    def walk(item: ft.Control) -> None:
        if isinstance(item, ft.Text):
            values.append(str(item.value or ""))
        content = getattr(item, "content", None)
        if isinstance(content, ft.Control):
            walk(content)
        for child in getattr(item, "controls", ()) or ():
            if isinstance(child, ft.Control):
                walk(child)

    walk(control)
    return values


def _admin() -> UserSummary:
    return UserSummary(
        id=1,
        username="admin",
        email="admin@example.com",
        first_name="Administrador",
        last_name="Laboratório",
        role="admin",
        is_active=True,
        onboarding_completed=True,
        last_login_at=None,
    )


def test_shell_keeps_ui_fix7_navigation_even_after_legacy_monkeypatch(monkeypatch) -> None:
    clicked: list[str] = []

    def broken_navigation_surface(**_kwargs):
        return ft.Container(
            width=20,
            height=20,
            content=ft.Icon(ft.Icons.BLOCK),
        )

    # R3/R6 historicamente substituem este nome no módulo shell durante o startup.
    # A UI-FIX-7 precisa usar a referência privada estável, não este nome mutável.
    monkeypatch.setattr(
        shell_module,
        "hoverable_navigation_surface",
        broken_navigation_surface,
        raising=False,
    )

    shell = shell_module.build_production_shell(
        ft.Container(),
        selected_view="new_test",
        on_dashboard=lambda: clicked.append("dashboard"),
        on_tests=lambda: clicked.append("tests"),
        on_new_test=lambda: clicked.append("new_test"),
        on_agenda=lambda: clicked.append("agenda"),
        on_history=lambda: clicked.append("history"),
        on_notifications=lambda: clicked.append("notifications"),
        on_help=lambda: clicked.append("help"),
        on_settings=lambda: clicked.append("settings"),
        on_users=lambda: clicked.append("users"),
        on_logout=lambda: clicked.append("logout"),
        on_github=lambda: clicked.append("github"),
        on_toggle_sidebar=lambda: clicked.append("toggle"),
        current_user=_admin(),
        layout=LayoutProfile.for_mode("regular"),
        notification_count=2,
    )

    sidebar = shell.controls[0]
    navigation = sidebar.content.controls[2]
    dashboard = navigation.controls[0]
    new_test = navigation.controls[2]

    assert "Dashboard" in _texts(dashboard)
    assert "Novo ensaio" in _texts(new_test)
    assert dashboard.width == 212
    assert new_test.width == 212

    dashboard.on_click(None)
    assert clicked == ["dashboard"]
