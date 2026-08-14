"""Regressões críticas preservadas na estabilização final 0.8.5."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import flet as ft

from climatetest_manager import __version__
from climatetest_manager.config import EmailSettings
from climatetest_manager.repositories.climate_tests import (
    NotificationStatus,
    SystemIncidentSummary,
)
from climatetest_manager.round7_runtime import TABLE17_MODE
from climatetest_manager.services.auth import UserSummary
from climatetest_manager.services.network import ServerIdentity
from climatetest_manager.ui.responsive import LayoutProfile
from climatetest_manager.ui.views.final_new_test import FinalNewTestView
from climatetest_manager.v084_stability import (
    _compact_settings_builder,
    _compose_shell,
    _replace_shell_frame,
    _walk,
)


def _texts(control: ft.Control) -> list[str]:
    values: list[str] = []
    for item in _walk(control):
        if isinstance(item, ft.Text):
            values.append(str(item.value or ""))
        elif isinstance(item, ft.Button):
            values.append(str(item.content or ""))
    return values


def _admin() -> UserSummary:
    return UserSummary(
        id=1,
        username="admin",
        email="admin@example.com",
        first_name="Admin",
        last_name="Laboratório",
        role="admin",
        is_active=True,
        onboarding_completed=True,
        last_login_at=None,
    )


def test_table17_keeps_one_tree_and_service_temperature_has_one_parent() -> None:
    view = FinalNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
    table = view._interactive_table
    option_cells = tuple(cell for _row, _option, cell in table._option_cells)

    view.mode_group.value = TABLE17_MODE
    view._on_mode_change()
    view.service_temperature.value = "81"
    view._recalculate()
    view._select_table_epl("Gb")
    view._select_table_option("B")

    assert view._interactive_table is table
    assert tuple(cell for _row, _option, cell in table._option_cells) == option_cells
    assert sum(item is view.service_temperature for item in _walk(view.root)) == 1
    assert view._condition.rule_id == "G1-HIGH-B"


def test_save_stays_clickable_so_missing_fields_can_be_highlighted() -> None:
    view = FinalNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
    view.mode_group.value = TABLE17_MODE
    view._on_mode_change()

    assert view.save_button.disabled is False
    view._submit()
    assert view.client.error == "Campo obrigatório."
    assert view.process_number.error == "Campo obrigatório."
    assert view.product.error == "Campo obrigatório."
    assert view.service_temperature.error == "Campo obrigatório."


def test_sidebar_refresh_never_reparents_or_replaces_current_screen() -> None:
    content = ft.Column(controls=[ft.Text("Tela persistente")])
    repository = SimpleNamespace(list_user_notifications=lambda **_kwargs: [])
    app = SimpleNamespace(
        _layout=LayoutProfile.from_width(1280),
        _sidebar_collapsed=False,
        _selected_view="dashboard",
        _current_user=_admin(),
        _production_repository=repository,
        show_dashboard=lambda: None,
        show_tests=lambda: None,
        show_new_test=lambda: None,
        show_agenda=lambda: None,
        show_history=lambda: None,
        show_notifications=lambda: None,
        show_help=lambda: None,
        show_settings=lambda: None,
        show_users=lambda: None,
        _confirm_logout=lambda: None,
        _open_github=lambda: None,
        _toggle_sidebar=lambda: None,
    )
    shell = _compose_shell(app, content)
    app._v084_shell = shell
    app._v084_content_host = shell.controls[1]
    old_sidebar = shell.controls[0]

    app._sidebar_collapsed = True
    _replace_shell_frame(app)

    assert app._v084_content_host.content is content
    assert shell.controls[0] is not old_sidebar
    assert app._v084_content_host.padding == LayoutProfile.from_width(1280).content_padding


def test_settings_distinguishes_smtp_test_from_automatic_alerts() -> None:
    async def no_op_async(_event: object | None = None) -> None:
        return None

    incident = SystemIncidentSummary(
        id=1,
        reason_code="software_crash",
        category="Falha do software",
        severity="Alta",
        description="Falha controlada para validar o painel.",
        immediate_action="Operação interrompida e registros conferidos.",
        status="open",
        reported_by="Operador",
        reported_at=datetime(2026, 8, 13, 10, 30, tzinfo=UTC),
        corrective_action=None,
        resolved_by=None,
        resolved_at=None,
    )
    root = _compact_settings_builder(
        identity=ServerIdentity("LAB-SERVER", ("192.168.1.10",)),
        database_path=Path("C:/ProgramData/ClimateTestManager/data.db"),
        backup_directory=Path("C:/Backups"),
        notifications_enabled=True,
        notification_status=NotificationStatus(),
        email_settings=EmailSettings(
            enabled=False,
            host="smtp.example.com",
            port=587,
            sender="admin@example.com",
            username="admin@example.com",
            password="secret",
        ),
        email_recipients=["admin@example.com"],
        system_incidents=[incident],
        theme_mode="light",
        current_user=_admin(),
        on_theme_change=lambda _mode: None,
        on_change_password=lambda *_args: None,
        on_manage_users=lambda: None,
        on_help=lambda: None,
        on_enable_notifications=lambda: None,
        on_disable_notifications=lambda: None,
        on_test_notification=lambda: None,
        on_save_email_settings=lambda _settings, _password: None,
        on_test_email=lambda: None,
        on_select_profile_photo=no_op_async,
        on_remove_profile_photo=lambda: None,
        on_open_data_folder=lambda: None,
        on_backup=no_op_async,
        on_configure_backup=no_op_async,
        on_report_system_incident=lambda *_args: None,
        on_resolve_system_incident=lambda *_args: None,
        on_refresh=lambda: None,
        on_rotate_administrator_recovery=lambda: "recovery-code",
    )
    text = _texts(root)

    assert isinstance(root, ft.Column)
    assert root.scroll == ft.ScrollMode.AUTO
    assert "Automação desativada" in text
    assert "Ativar automação" in text
    assert "Abrir log de falhas" in text
    assert incident.description not in text


def test_release_and_installer_use_one_consistent_version_and_one_server_guard() -> None:
    project = Path(__file__).resolve().parents[2]
    installer = (project / "installer" / "ClimateTestManager.iss").read_text(encoding="utf-8")
    build = (project / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")
    workflow = (project / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    marker = (project / "src" / "assets" / "server-build.txt").read_text(encoding="utf-8")
    server_install = (project / "scripts" / "install_server_tasks.ps1").read_text(encoding="utf-8")

    assert __version__ == "0.8.5"
    assert '#define MyAppVersion "0.8.5"' in installer
    assert '#define MyBuildRevision "R9-20260814"' in installer
    assert "ClimateTestManager-v{#MyAppVersion}" in installer
    assert "ForeignServerFound" in installer
    assert "Somente um servidor central" in installer
    assert "[InstallDelete]" in installer
    assert '$version = "0.8.5"' in build
    assert "payloadVersion" not in build
    assert "ClimateTestManager-Setup-v0.8.5.exe" in workflow
    assert '([string]$response.Content).Trim() -eq "R9-20260814"' in workflow
    assert "v0.8.0" not in workflow
    assert '$buildRevision = "R9-20260814"' in server_install
    assert "/server-build.txt" in server_install
    assert marker.strip() == "R9-20260814"
