"""Ajustes da tela de configurações quando a UI é servida pela máquina central."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

from climatetest_manager.config import EmailSettings
from climatetest_manager.repositories.climate_tests import NotificationStatus, SystemIncidentSummary
from climatetest_manager.services.auth import UserSummary
from climatetest_manager.services.network import ServerIdentity
from climatetest_manager.ui.views.server_status import build_server_status_card
from climatetest_manager.ui.views.settings import build_settings_view


def _enable_local_notification_test(control: ft.Control) -> None:
    """O teste agora é entregue pelo host desktop da estação, não pela sessão do servidor."""

    if isinstance(control, ft.Button) and control.content == "Testar notificação":
        control.disabled = False
        control.tooltip = "Exibir uma notificação no Windows deste computador"
    child = getattr(control, "content", None)
    if isinstance(child, ft.Control):
        _enable_local_notification_test(child)
    children = getattr(control, "controls", None)
    if isinstance(children, list):
        for item in children:
            if isinstance(item, ft.Control):
                _enable_local_notification_test(item)


def build_managed_settings_view(
    *,
    identity: ServerIdentity,
    database_path: Path,
    backup_directory: Path | None,
    notifications_enabled: bool,
    notification_status: NotificationStatus,
    email_settings: EmailSettings,
    email_recipients: list[str],
    system_incidents: list[SystemIncidentSummary],
    theme_mode: str,
    current_user: UserSummary,
    on_theme_change: Callable[[str], None],
    on_change_password: Callable[[str, str, str], None],
    on_manage_users: Callable[[], None] | None,
    on_help: Callable[[], None],
    on_enable_notifications: Callable[[], None],
    on_disable_notifications: Callable[[], None],
    on_test_notification: Callable[[], None],
    on_save_email_settings: Callable[[EmailSettings, str], str | None],
    on_test_email: Callable[[], None],
    on_select_profile_photo: Callable[[object | None], Awaitable[None]],
    on_remove_profile_photo: Callable[[], None],
    on_open_data_folder: Callable[[], None],
    on_backup: Callable[[object | None], Awaitable[None]],
    on_configure_backup: Callable[[object | None], Awaitable[None]] | None,
    on_report_system_incident: Callable[[str, str, str], str | None],
    on_resolve_system_incident: Callable[[int, str], str | None] | None,
    on_refresh: Callable[[], None],
    on_rotate_administrator_recovery: Callable[[], str] | None = None,
) -> ft.Column:
    """Mantém a tela consolidada e acrescenta infraestrutura sem duplicar o layout."""

    content = build_settings_view(
        database_path=database_path,
        backup_directory=backup_directory,
        notifications_enabled=notifications_enabled,
        notification_status=notification_status,
        email_settings=email_settings,
        email_recipients=email_recipients,
        system_incidents=system_incidents,
        theme_mode=theme_mode,
        current_user=current_user,
        on_theme_change=on_theme_change,
        on_change_password=on_change_password,
        on_manage_users=on_manage_users,
        on_help=on_help,
        on_enable_notifications=on_enable_notifications,
        on_disable_notifications=on_disable_notifications,
        on_test_notification=on_test_notification,
        on_save_email_settings=on_save_email_settings,
        on_test_email=on_test_email,
        on_select_profile_photo=on_select_profile_photo,
        on_remove_profile_photo=on_remove_profile_photo,
        on_open_data_folder=on_open_data_folder,
        on_backup=on_backup,
        on_configure_backup=on_configure_backup,
        on_report_system_incident=on_report_system_incident,
        on_resolve_system_incident=on_resolve_system_incident,
        on_refresh=on_refresh,
        on_rotate_administrator_recovery=on_rotate_administrator_recovery,
        allow_theme_change=True,
        managed_server_mode=True,
    )
    infrastructure = build_server_status_card(
        identity,
        backup_directory=backup_directory,
        is_admin=current_user.is_admin,
        on_configure_backup=on_configure_backup,
    )
    # Cabeçalho + conta continuam primeiro; infraestrutura aparece antes das integrações.
    content.controls.insert(2, infrastructure)
    _enable_local_notification_test(content)
    return content
