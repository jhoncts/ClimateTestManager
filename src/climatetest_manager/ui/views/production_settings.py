"""Ajustes finais de Configurações para a experiência multiestação."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

from climatetest_manager.config import EmailSettings
from climatetest_manager.domain.incidents import INCIDENT_REASONS, incident_reason
from climatetest_manager.repositories.climate_tests import NotificationStatus, SystemIncidentSummary
from climatetest_manager.services.auth import UserSummary
from climatetest_manager.services.network import ServerIdentity
from climatetest_manager.ui.components import dialog_actions, dialog_banner, styled_dialog
from climatetest_manager.ui.interaction import apply_interaction_polish, glass_surface
from climatetest_manager.ui.theme import AppColors, THEME_OPTIONS
from climatetest_manager.ui.views.server_status import build_server_status_card
from climatetest_manager.ui.views.settings import build_settings_view


def _walk(control: ft.Control):
    yield control
    child = getattr(control, "content", None)
    if isinstance(child, ft.Control):
        yield from _walk(child)
    children = getattr(control, "controls", None)
    if isinstance(children, list):
        for item in children:
            if isinstance(item, ft.Control):
                yield from _walk(item)
    actions = getattr(control, "actions", None)
    if isinstance(actions, list):
        for item in actions:
            if isinstance(item, ft.Control):
                yield from _walk(item)


def _button_label(control: ft.Control) -> str:
    if not isinstance(control, (ft.Button, ft.TextButton, ft.IconButton)):
        return ""
    content = getattr(control, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, ft.Text):
        return content.value or ""
    return ""


def _theme_card(theme_mode: str, on_theme_change: Callable[[str], None]) -> ft.Container:
    selector = ft.Dropdown(
        label="Tema deste computador",
        value=theme_mode if theme_mode in {item[0] for item in THEME_OPTIONS} else "light",
        options=[
            ft.DropdownOption(key=key, text=f"{label} — {description}")
            for key, label, description in THEME_OPTIONS
        ],
        width=420,
    )
    selector.on_select = lambda _event: on_theme_change(selector.value or "light")
    return glass_surface(
        ft.ResponsiveRow(
            spacing=14,
            run_spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    col={"xs": 12, "md": 6},
                    content=ft.Column(
                        spacing=3,
                        controls=[
                            ft.Text(
                                "Aparência",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            ft.Text(
                                "A escolha fica salva somente neste dispositivo. Alterar o tema "
                                "aqui não muda o servidor nem outras estações.",
                                size=11,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                ),
                ft.Container(
                    col={"xs": 12, "md": 6},
                    alignment=ft.Alignment.CENTER_RIGHT,
                    content=selector,
                ),
            ],
        ),
        padding=18,
        accent=True,
    )


def _replace_incident_dialog(
    content: ft.Control,
    *,
    on_report_system_incident: Callable[[str, str, str], str | None],
    on_refresh: Callable[[], None],
) -> None:
    target = next(
        (
            control
            for control in _walk(content)
            if isinstance(control, ft.Button) and _button_label(control) == "Registrar falha"
        ),
        None,
    )
    if not isinstance(target, ft.Button):
        return

    def show_dialog(_event: object | None = None) -> None:
        page = target.page
        reason_selector = ft.Dropdown(
            label="Motivo da falha",
            value="software_crash",
            options=[
                ft.DropdownOption(key=reason.code, text=reason.label) for reason in INCIDENT_REASONS
            ],
        )
        reason = incident_reason("software_crash")
        priority = ft.Text(
            f"Prioridade automática: {reason.severity}",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=AppColors.WARNING,
        )
        guidance = ft.Text(reason.guidance, size=10, color=AppColors.TEXT_SECONDARY)
        description = ft.TextField(
            label="O que aconteceu?",
            hint_text="Descreva a falha e o que foi afetado.",
            multiline=True,
            min_lines=3,
            max_lines=5,
            max_length=2000,
            on_change=lambda _event: None,
        )
        immediate_action = ft.TextField(
            label="Qual ação você tomou ao reconhecer a falha?",
            hint_text="Ex.: interrompi a operação e conferi os registros.",
            multiline=True,
            min_lines=2,
            max_lines=4,
            max_length=2000,
            on_change=lambda _event: None,
        )
        error = ft.Text("", size=10, color=AppColors.DANGER)
        progress = ft.ProgressRing(width=18, height=18, stroke_width=2, visible=False)
        submitted = False

        def update_priority(_event: object | None = None) -> None:
            selected = incident_reason(reason_selector.value or "other")
            priority.value = f"Prioridade automática: {selected.severity}"
            priority.color = (
                AppColors.DANGER if selected.severity in {"Crítica", "Alta"} else AppColors.WARNING
            )
            guidance.value = selected.guidance
            page.update(priority, guidance)

        reason_selector.on_select = update_priority
        save_button = ft.Button(
            content="Salvar registro",
            icon=ft.Icons.SAVE_OUTLINED,
            bgcolor=AppColors.PRIMARY,
            color=AppColors.WHITE,
        )

        def confirm(_confirm_event: object | None = None) -> None:
            nonlocal submitted
            if submitted:
                return
            description_value = description.value.strip()
            action_value = immediate_action.value.strip()
            if len(description_value) < 10:
                error.value = "Descreva a falha com pelo menos 10 caracteres."
                error.update()
                return
            if len(action_value) < 10:
                error.value = "Informe a ação imediata com pelo menos 10 caracteres."
                error.update()
                return
            submitted = True
            save_button.disabled = True
            save_button.content = "Salvando..."
            progress.visible = True
            error.value = ""
            page.update(save_button, progress, error)
            result = on_report_system_incident(
                reason_selector.value or "other",
                description_value,
                action_value,
            )
            if result:
                submitted = False
                save_button.disabled = False
                save_button.content = "Salvar registro"
                progress.visible = False
                error.value = result
                page.update(save_button, progress, error)
                return
            page.pop_dialog()
            on_refresh()

        save_button.on_click = confirm
        dialog = styled_dialog(
            title="Registrar falha do sistema",
            subtitle="Um clique gera um único registro e um único alerta administrativo",
            icon=ft.Icons.BUG_REPORT_OUTLINED,
            scrollable=True,
            content=ft.Container(
                width=600,
                content=ft.Column(
                    tight=True,
                    spacing=11,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        dialog_banner(
                            "A prioridade é definida automaticamente pelo motivo. Descreva "
                            "somente o necessário para entender o impacto e a contenção."
                        ),
                        reason_selector,
                        ft.Container(
                            border_radius=11,
                            bgcolor=AppColors.WARNING_LIGHT,
                            padding=11,
                            content=ft.Column(spacing=2, controls=[priority, guidance]),
                        ),
                        description,
                        immediate_action,
                        error,
                        ft.Row(
                            alignment=ft.MainAxisAlignment.END,
                            spacing=7,
                            controls=[progress],
                        ),
                    ],
                ),
            ),
            actions=[
                ft.TextButton(content="Voltar", on_click=lambda _event: page.pop_dialog()),
                save_button,
            ],
        )
        page.show_dialog(apply_interaction_polish(dialog))

    target.on_click = show_dialog


def build_production_settings_view(
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
    """Monta as configurações de servidor mantendo preferências visuais locais."""

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

    # Remove o switch antigo para não manter duas fontes de verdade para aparência.
    for control in _walk(content):
        if isinstance(control, ft.Switch) and control.label == "Usar tema escuro":
            control.visible = False
        if isinstance(control, ft.Button):
            label = _button_label(control)
            if label == "Desativar avisos":
                control.disabled = not notifications_enabled
            elif label == "Ativar avisos":
                control.disabled = notifications_enabled
            elif label == "Testar notificação":
                control.disabled = False

    infrastructure = build_server_status_card(
        identity,
        backup_directory=backup_directory,
        is_admin=current_user.is_admin,
        on_configure_backup=on_configure_backup,
    )
    # Cabeçalho e conta ficam primeiro. Aparência e infraestrutura aparecem antes das integrações.
    content.controls.insert(2, _theme_card(theme_mode, on_theme_change))
    content.controls.insert(3, infrastructure)
    _replace_incident_dialog(
        content,
        on_report_system_incident=on_report_system_incident,
        on_refresh=on_refresh,
    )
    apply_interaction_polish(content)
    return content
