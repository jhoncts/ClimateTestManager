"""Configurações da conta, aparência, notificações e armazenamento."""

from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

from climatetest_manager import __version__
from climatetest_manager.config import EmailSettings
from climatetest_manager.database.migrations import SCHEMA_VERSION
from climatetest_manager.domain.climate_rules import NORMATIVE_RULE_VERSION
from climatetest_manager.domain.incidents import INCIDENT_REASONS, incident_reason
from climatetest_manager.repositories.climate_tests import (
    NotificationStatus,
    SystemIncidentSummary,
)
from climatetest_manager.services.auth import UserSummary
from climatetest_manager.ui.components import (
    dialog_actions,
    dialog_banner,
    styled_dialog,
    user_avatar,
)
from climatetest_manager.ui.email_help import EMAIL_PROVIDER_NOTES, EMAIL_SETUP_STEPS
from climatetest_manager.ui.formatters import format_datetime
from climatetest_manager.ui.theme import AppColors


def build_settings_view(
    *,
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
    allow_theme_change: bool = True,
    managed_server_mode: bool = False,
) -> ft.Column:
    """Monta conta, preferências locais e integrações do Windows."""

    status_color = AppColors.PRIMARY if notifications_enabled else AppColors.WARNING
    status_text = "Ativo" if notifications_enabled else "Inativo"
    if notification_status.last_checked_at is None:
        last_result = "O agente ainda não registrou nenhuma verificação."
    elif notification_status.failed_count:
        last_result = (
            f"Última verificação: {notification_status.failed_count} falha(s). "
            f"{notification_status.last_error or ''}"
        ).strip()
    elif notification_status.delivered_count:
        last_result = (
            f"Última verificação: {notification_status.delivered_count} aviso(s) enviado(s)."
        )
    else:
        last_result = "Última verificação concluída, sem avisos pendentes."
    theme_switch = ft.Switch(
        label="Usar tema escuro",
        value=theme_mode == "dark",
        disabled=not allow_theme_change,
        tooltip=(
            None
            if allow_theme_change
            else "No modo servidor, o tema é mantido igual entre todas as sessões."
        ),
    )
    theme_switch.on_change = lambda _event: on_theme_change(
        "dark" if theme_switch.value else "light"
    )
    password_button = ft.Button(
        content="Alterar minha senha",
        icon=ft.Icons.PASSWORD,
    )

    def show_password_dialog(_event: object | None = None) -> None:
        current_password = ft.TextField(
            label="Senha atual",
            password=True,
            can_reveal_password=True,
            max_length=128,
            counter="",
        )
        new_password = ft.TextField(
            label="Nova senha",
            password=True,
            can_reveal_password=True,
            max_length=128,
            counter="",
        )
        confirmation = ft.TextField(
            label="Confirmar nova senha",
            password=True,
            can_reveal_password=True,
            max_length=128,
            counter="",
        )
        page = password_button.page

        def confirm(_event: object | None = None) -> None:
            page.pop_dialog()
            on_change_password(
                current_password.value,
                new_password.value,
                confirmation.value,
            )

        page.show_dialog(
            styled_dialog(
                title="Alterar minha senha",
                subtitle="A sessão atual será encerrada depois da alteração",
                icon=ft.Icons.PASSWORD,
                content=ft.Column(
                    tight=True,
                    width=460,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        dialog_banner(
                            "Use no mínimo 8 caracteres, incluindo uma letra e um número."
                        ),
                        current_password,
                        new_password,
                        confirmation,
                        ft.Text(
                            "Após a alteração, entre novamente com a nova senha.",
                            size=11,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
                actions=dialog_actions(
                    page=page,
                    primary_label="Alterar senha",
                    primary_icon=ft.Icons.PASSWORD,
                    on_confirm=confirm,
                ),
            )
        )

    password_button.on_click = show_password_dialog
    recovery_button = ft.Button(
        content="Renovar código de recuperação",
        icon=ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
    )

    def show_recovery_code_dialog(_event: object | None = None) -> None:
        if on_rotate_administrator_recovery is None:
            return
        page = recovery_button.page
        try:
            recovery_code = on_rotate_administrator_recovery()
        except ValueError as error:
            page.show_dialog(
                styled_dialog(
                    title="Não foi possível renovar o código",
                    subtitle=str(error),
                    icon=ft.Icons.ERROR_OUTLINE,
                    actions=[
                        ft.Button(
                            content="Fechar",
                            on_click=lambda _close_event: page.pop_dialog(),
                        )
                    ],
                )
            )
            return
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Novo código de recuperação"),
                content=ft.Column(
                    width=540,
                    tight=True,
                    spacing=12,
                    controls=[
                        ft.Text(
                            "O código anterior foi invalidado. Guarde este valor fora do "
                            "servidor; ele não será exibido novamente."
                        ),
                        ft.Container(
                            border_radius=12,
                            bgcolor=AppColors.INFO_LIGHT,
                            padding=16,
                            content=ft.Text(
                                recovery_code,
                                size=19,
                                weight=ft.FontWeight.BOLD,
                                selectable=True,
                            ),
                        ),
                    ],
                ),
                actions=[
                    ft.Button(
                        content="Já guardei em local seguro",
                        icon=ft.Icons.VERIFIED_USER_OUTLINED,
                        on_click=lambda _close_event: page.pop_dialog(),
                    )
                ],
            )
        )

    recovery_button.on_click = show_recovery_code_dialog
    email_button = ft.Button(
        content="Configurar e-mail",
        icon=ft.Icons.MARK_EMAIL_READ_OUTLINED,
    )

    def show_email_dialog(_event: object | None = None) -> None:
        configured_provider = (
            "gmail"
            if email_settings.host.casefold() == "smtp.gmail.com"
            else "microsoft"
            if email_settings.host.casefold() == "smtp.office365.com"
            else "other"
        )
        provider = ft.Dropdown(
            label="Modelo de configuração",
            value=configured_provider,
            options=[
                ft.DropdownOption(key="gmail", text="Gmail — senha de app"),
                ft.DropdownOption(
                    key="microsoft",
                    text="Microsoft 365 — confirmar com a TI",
                ),
                ft.DropdownOption(key="other", text="Outro provedor"),
            ],
            border_radius=10,
        )
        host = ft.TextField(
            label="Servidor SMTP",
            value=email_settings.host,
            hint_text="Ex.: smtp.office365.com",
            max_length=255,
            counter="",
        )
        port = ft.TextField(
            label="Porta",
            value=str(email_settings.port),
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9]"),
            max_length=5,
            counter="",
        )
        sender = ft.TextField(
            label="E-mail remetente",
            value=email_settings.sender,
            keyboard_type=ft.KeyboardType.EMAIL,
            max_length=254,
            counter="",
        )
        username = ft.TextField(
            label="Usuário SMTP",
            value=email_settings.username,
            hint_text="Normalmente é o e-mail completo",
            max_length=254,
            counter="",
        )
        password = ft.TextField(
            label=(
                "Nova senha SMTP (deixe em branco para manter)"
                if email_settings.password
                else "Senha SMTP"
            ),
            password=True,
            can_reveal_password=True,
            max_length=256,
            counter="",
        )
        password_note = ft.Text(
            "No Gmail, cole a senha de app como ela aparece: os espaços serão removidos "
            "automaticamente.",
            size=10,
            color=AppColors.TEXT_SECONDARY,
        )
        use_tls = ft.Switch(label="Usar conexão TLS", value=email_settings.use_tls)
        enabled = ft.Switch(
            label="Enviar e-mails automáticos",
            # Na primeira configuração o comportamento esperado é salvar e já
            # ativar os alertas. Uma conta existente que foi desativada de forma
            # explícita continua respeitando essa escolha.
            value=email_settings.enabled or not email_settings.has_credentials,
        )
        error_text = ft.Text("", size=11, color=AppColors.DANGER)
        page = email_button.page
        provider_notes = {
            "gmail": EMAIL_PROVIDER_NOTES[0][1],
            "microsoft": EMAIL_PROVIDER_NOTES[1][1],
            "other": EMAIL_PROVIDER_NOTES[2][1],
        }
        provider_note = ft.Text(
            provider_notes[configured_provider],
            size=11,
            color=AppColors.TEXT_SECONDARY,
        )

        def apply_provider(_event: object | None = None) -> None:
            selected = provider.value or "other"
            if selected == "gmail":
                host.value = "smtp.gmail.com"
                port.value = "587"
                use_tls.value = True
                provider_note.value = EMAIL_PROVIDER_NOTES[0][1]
            elif selected == "microsoft":
                host.value = "smtp.office365.com"
                port.value = "587"
                use_tls.value = True
                provider_note.value = EMAIL_PROVIDER_NOTES[1][1]
            else:
                provider_note.value = EMAIL_PROVIDER_NOTES[2][1]
            page.update(host, port, use_tls, provider_note)

        provider.on_select = apply_provider

        tutorial = ft.ExpansionTile(
            title=ft.Text(
                "Como configurar, passo a passo",
                size=13,
                weight=ft.FontWeight.BOLD,
                color=AppColors.TEXT_PRIMARY,
            ),
            subtitle=ft.Text(
                "Abra para conferir antes de salvar",
                size=10,
                color=AppColors.TEXT_SECONDARY,
            ),
            leading=ft.Icons.HELP_OUTLINE,
            maintain_state=True,
            tile_padding=ft.Padding.symmetric(horizontal=12, vertical=4),
            controls_padding=ft.Padding.only(left=14, right=14, bottom=12),
            bgcolor=AppColors.PAGE_BACKGROUND,
            collapsed_bgcolor=AppColors.PAGE_BACKGROUND,
            shape=ft.RoundedRectangleBorder(radius=12),
            collapsed_shape=ft.RoundedRectangleBorder(radius=12),
            controls=[
                ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            spacing=9,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Container(
                                    width=24,
                                    height=24,
                                    border_radius=12,
                                    bgcolor=AppColors.PRIMARY_LIGHT,
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Text(
                                        str(index),
                                        size=10,
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.PRIMARY,
                                    ),
                                ),
                                ft.Text(step, expand=True, size=11),
                            ],
                        )
                        for index, step in enumerate(EMAIL_SETUP_STEPS, start=1)
                    ],
                )
            ],
        )

        def confirm(_event: object | None = None) -> None:
            try:
                parsed_port = int(port.value)
            except (TypeError, ValueError):
                error_text.value = "Informe uma porta SMTP válida."
                error_text.update()
                return
            settings = EmailSettings(
                enabled=bool(enabled.value),
                host=host.value,
                port=parsed_port,
                sender=sender.value,
                username=username.value,
                password=email_settings.password,
                use_tls=bool(use_tls.value),
            )
            error = on_save_email_settings(settings, password.value)
            if error:
                error_text.value = error
                error_text.update()
                return
            page.pop_dialog()

        page.show_dialog(
            styled_dialog(
                title="Configurar avisos por e-mail",
                subtitle="Lembretes de retirada e atraso para usuários ativos",
                icon=ft.Icons.MARK_EMAIL_READ_OUTLINED,
                scrollable=True,
                content=ft.Column(
                    width=640,
                    tight=True,
                    spacing=14,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        dialog_banner(
                            "Os avisos serão enviados para todos os usuários ativos: "
                            "2 horas antes da retirada nominal e quando o limite for ultrapassado."
                        ),
                        ft.Container(
                            border_radius=12,
                            bgcolor=AppColors.PAGE_BACKGROUND,
                            border=ft.Border.all(1, AppColors.DIVIDER),
                            padding=12,
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                wrap=True,
                                run_spacing=8,
                                controls=[
                                    ft.Text(
                                        "Envio automático",
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    enabled,
                                ],
                            ),
                        ),
                        provider,
                        provider_note,
                        ft.ResponsiveRow(
                            spacing=12,
                            run_spacing=10,
                            controls=[
                                ft.Container(col={"xs": 12, "sm": 8}, content=host),
                                ft.Container(col={"xs": 12, "sm": 4}, content=port),
                                ft.Container(col={"xs": 12, "sm": 6}, content=sender),
                                ft.Container(col={"xs": 12, "sm": 6}, content=username),
                            ],
                        ),
                        ft.Column(spacing=4, controls=[password, password_note]),
                        ft.Container(
                            border_radius=12,
                            bgcolor=AppColors.PAGE_BACKGROUND,
                            border=ft.Border.all(1, AppColors.DIVIDER),
                            padding=12,
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                wrap=True,
                                run_spacing=8,
                                controls=[
                                    ft.Column(
                                        spacing=2,
                                        controls=[
                                            ft.Text(
                                                "Segurança da conexão",
                                                size=12,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            ft.Text(
                                                "A senha fica protegida pela conta do Windows.",
                                                size=10,
                                                color=AppColors.TEXT_SECONDARY,
                                            ),
                                        ],
                                    ),
                                    use_tls,
                                ],
                            ),
                        ),
                        tutorial,
                        error_text,
                    ],
                ),
                actions=dialog_actions(
                    page=page,
                    primary_label="Salvar configuração",
                    primary_icon=ft.Icons.SAVE_OUTLINED,
                    on_confirm=confirm,
                ),
            )
        )

    email_button.on_click = show_email_dialog
    remove_photo_button = ft.Button(
        content="Remover foto",
        icon=ft.Icons.NO_PHOTOGRAPHY_OUTLINED,
        disabled=not bool(current_user.profile_photo_b64),
    )
    disable_notifications_button = ft.Button(
        content="Desativar avisos",
        icon=ft.Icons.NOTIFICATIONS_OFF,
        disabled=not notifications_enabled or managed_server_mode,
    )

    def confirm_remove_photo(_event: object | None = None) -> None:
        page = remove_photo_button.page

        def confirm(_confirm_event: object | None = None) -> None:
            page.pop_dialog()
            on_remove_profile_photo()

        page.show_dialog(
            styled_dialog(
                title="Remover a foto do perfil?",
                subtitle=f"Conta @{current_user.username}",
                icon=ft.Icons.NO_PHOTOGRAPHY_OUTLINED,
                danger=True,
                content=ft.Container(
                    width=460,
                    content=dialog_banner(
                        "A imagem salva no banco será removida. O nome e os demais dados da "
                        "conta não serão alterados.",
                        icon=ft.Icons.WARNING_AMBER,
                        danger=True,
                    ),
                ),
                actions=dialog_actions(
                    page=page,
                    primary_label="Remover foto",
                    primary_icon=ft.Icons.NO_PHOTOGRAPHY_OUTLINED,
                    on_confirm=confirm,
                    danger=True,
                    cancel_label="Manter foto",
                ),
            )
        )

    def confirm_disable_notifications(_event: object | None = None) -> None:
        page = disable_notifications_button.page

        def confirm(_confirm_event: object | None = None) -> None:
            page.pop_dialog()
            on_disable_notifications()

        page.show_dialog(
            styled_dialog(
                title="Desativar os avisos?",
                subtitle="A verificação automática de prazos será interrompida",
                icon=ft.Icons.NOTIFICATIONS_OFF_OUTLINED,
                danger=True,
                content=ft.Container(
                    width=500,
                    content=dialog_banner(
                        "A Agenda continuará disponível, mas o Windows e o e-mail não avisarão "
                        "automaticamente enquanto esta função estiver desativada.",
                        icon=ft.Icons.WARNING_AMBER,
                        danger=True,
                    ),
                ),
                actions=dialog_actions(
                    page=page,
                    primary_label="Desativar avisos",
                    primary_icon=ft.Icons.NOTIFICATIONS_OFF,
                    on_confirm=confirm,
                    danger=True,
                    cancel_label="Manter avisos ativos",
                ),
            )
        )

    remove_photo_button.on_click = confirm_remove_photo
    disable_notifications_button.on_click = confirm_disable_notifications

    report_incident_button = ft.Button(
        content="Registrar falha",
        icon=ft.Icons.BUG_REPORT_OUTLINED,
        bgcolor=AppColors.PRIMARY,
        color=AppColors.WHITE,
    )

    def show_report_incident_dialog(_event: object | None = None) -> None:
        reason_selector = ft.Dropdown(
            label="Motivo da falha",
            value="software_crash",
            options=[
                ft.DropdownOption(key=reason.code, text=reason.label) for reason in INCIDENT_REASONS
            ],
        )
        initial_reason = incident_reason("software_crash")
        priority_text = ft.Text(
            f"Prioridade automática: {initial_reason.severity}",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=AppColors.DANGER,
        )
        guidance_text = ft.Text(
            initial_reason.guidance,
            size=11,
            color=AppColors.TEXT_SECONDARY,
        )
        priority_card = ft.Container(
            border_radius=11,
            bgcolor=AppColors.WARNING_LIGHT,
            padding=12,
            content=ft.Column(spacing=3, controls=[priority_text, guidance_text]),
        )

        def update_priority(_event: object | None = None) -> None:
            reason = incident_reason(reason_selector.value or "other")
            priority_text.value = f"Prioridade automática: {reason.severity}"
            priority_text.color = (
                AppColors.DANGER if reason.severity in {"Crítica", "Alta"} else AppColors.WARNING
            )
            guidance_text.value = reason.guidance
            priority_card.update()

        reason_selector.on_select = update_priority
        description = ft.TextField(
            label="O que aconteceu?",
            hint_text="Descreva a falha, quando ocorreu e quais registros podem ter sido afetados.",
            multiline=True,
            min_lines=3,
            max_lines=6,
            max_length=2000,
        )
        immediate_action = ft.TextField(
            label="Qual ação você tomou ao reconhecer a falha?",
            hint_text="Ex.: interrompido o uso e conferidos os registros com a planilha de apoio.",
            multiline=True,
            min_lines=2,
            max_lines=5,
            max_length=2000,
        )
        error_text = ft.Text("", size=11, color=AppColors.DANGER)
        page = report_incident_button.page

        def confirm(_confirm_event: object | None = None) -> None:
            if len(description.value.strip()) < 10:
                error_text.value = "Descreva a falha com pelo menos 10 caracteres."
                error_text.update()
                return
            if len(immediate_action.value.strip()) < 10:
                error_text.value = "Informe a ação imediata com pelo menos 10 caracteres."
                error_text.update()
                return
            error = on_report_system_incident(
                reason_selector.value or "other",
                description.value.strip(),
                immediate_action.value.strip(),
            )
            if error:
                error_text.value = error
                error_text.update()
                return
            page.pop_dialog()
            on_refresh()

        page.show_dialog(
            styled_dialog(
                title="Registrar falha do sistema",
                subtitle="Evidência para avaliação de impacto e ação corretiva",
                icon=ft.Icons.BUG_REPORT_OUTLINED,
                content=ft.Column(
                    width=620,
                    tight=True,
                    spacing=12,
                    controls=[
                        dialog_banner(
                            "Registre também falhas sem perda de dados. Se algum resultado "
                            "puder ter sido afetado, interrompa o uso e aplique o procedimento "
                            "de trabalho não conforme do laboratório."
                        ),
                        reason_selector,
                        priority_card,
                        description,
                        immediate_action,
                        error_text,
                    ],
                ),
                actions=dialog_actions(
                    page=page,
                    primary_label="Salvar registro",
                    primary_icon=ft.Icons.SAVE_OUTLINED,
                    on_confirm=confirm,
                ),
            )
        )

    report_incident_button.on_click = show_report_incident_dialog

    def incident_control(incident: SystemIncidentSummary) -> ft.Control:
        is_open = incident.status == "open"
        severity_color = {
            "Crítica": AppColors.DANGER,
            "Alta": AppColors.DANGER,
            "Média": AppColors.WARNING,
            "Crítico": AppColors.DANGER,
            "Alto": AppColors.DANGER,
            "Médio": AppColors.WARNING,
        }.get(incident.severity, AppColors.INFO)
        resolve_button = ft.Button(
            content="Registrar ação corretiva e encerrar",
            icon=ft.Icons.TASK_ALT,
        )

        def show_resolution_dialog(_event: object | None = None) -> None:
            corrective_action = ft.TextField(
                label="Ação corretiva e verificação realizada",
                hint_text=(
                    "Informe a causa tratada, a correção aplicada e como foi verificada a eficácia."
                ),
                multiline=True,
                min_lines=3,
                max_lines=7,
                max_length=3000,
            )
            error_text = ft.Text("", size=11, color=AppColors.DANGER)
            page = resolve_button.page

            def confirm(_confirm_event: object | None = None) -> None:
                if len(corrective_action.value.strip()) < 15:
                    error_text.value = "Descreva o tratamento com pelo menos 15 caracteres."
                    error_text.update()
                    return
                if on_resolve_system_incident is None:
                    error_text.value = "Somente administradores podem encerrar uma falha."
                    error_text.update()
                    return
                error = on_resolve_system_incident(
                    incident.id,
                    corrective_action.value.strip(),
                )
                if error:
                    error_text.value = error
                    error_text.update()
                    return
                page.pop_dialog()
                on_refresh()

            page.show_dialog(
                styled_dialog(
                    title=f"Encerrar falha #{incident.id}?",
                    subtitle="O registro original será preservado",
                    icon=ft.Icons.TASK_ALT,
                    content=ft.Column(
                        width=580,
                        tight=True,
                        spacing=12,
                        controls=[
                            dialog_banner(
                                "Confirme somente após avaliar o impacto nos ensaios, executar "
                                "a correção e verificar sua eficácia."
                            ),
                            corrective_action,
                            error_text,
                        ],
                    ),
                    actions=dialog_actions(
                        page=page,
                        primary_label="Encerrar falha",
                        primary_icon=ft.Icons.TASK_ALT,
                        on_confirm=confirm,
                    ),
                )
            )

        resolve_button.on_click = show_resolution_dialog
        details: list[ft.Control] = [
            ft.Text(incident.description, size=12),
            ft.Text(
                f"Ação imediata: {incident.immediate_action}",
                size=11,
                color=AppColors.TEXT_SECONDARY,
            ),
        ]
        if incident.corrective_action:
            details.append(
                ft.Text(
                    f"Ação corretiva: {incident.corrective_action}",
                    size=11,
                    color=AppColors.TEXT_SECONDARY,
                    selectable=True,
                )
            )
        if is_open and on_resolve_system_incident is not None:
            details.append(resolve_button)
        return ft.Container(
            border_radius=12,
            border=ft.Border.all(1, AppColors.DIVIDER),
            padding=14,
            content=ft.Column(
                spacing=7,
                controls=[
                    ft.Row(
                        wrap=True,
                        run_spacing=6,
                        controls=[
                            ft.Text(
                                f"#{incident.id} • {incident.category}",
                                weight=ft.FontWeight.BOLD,
                                expand=True,
                            ),
                            ft.Container(
                                border_radius=16,
                                bgcolor=(
                                    AppColors.WARNING_LIGHT if is_open else AppColors.PRIMARY_LIGHT
                                ),
                                padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                                content=ft.Text(
                                    "Aberta" if is_open else "Encerrada",
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.WARNING if is_open else AppColors.PRIMARY,
                                ),
                            ),
                            ft.Text(
                                incident.severity,
                                size=10,
                                weight=ft.FontWeight.BOLD,
                                color=severity_color,
                            ),
                        ],
                    ),
                    ft.Text(
                        f"Registrada por {incident.reported_by} em "
                        f"{format_datetime(incident.reported_at, assume_utc=True)}",
                        size=10,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    *details,
                ],
            ),
        )

    automatic_recipients = ", ".join(email_recipients) or "Nenhum usuário ativo cadastrado."
    test_recipients = list(
        dict.fromkeys(
            [
                *email_recipients,
                *([email_settings.sender] if email_settings.sender else []),
            ]
        )
    )
    test_recipients_text = ", ".join(test_recipients) or "Nenhum destinatário disponível."
    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=20,
        controls=[
            ft.Column(
                spacing=3,
                controls=[
                    ft.Text(
                        "Configurações",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "Preferências locais e recursos executados pelo Windows.",
                        size=14,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                ],
            ),
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=16,
                padding=22,
                content=ft.Column(
                    spacing=14,
                    controls=[
                        ft.Row(
                            spacing=14,
                            wrap=True,
                            run_spacing=10,
                            controls=[
                                user_avatar(current_user, size=54),
                                ft.Column(
                                    spacing=3,
                                    controls=[
                                        ft.Text(
                                            current_user.full_name,
                                            size=17,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            f"@{current_user.username} • {current_user.email}",
                                            size=12,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                        ft.Text(
                                            f"Perfil: {current_user.role_label}",
                                            size=11,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.Row(
                            wrap=True,
                            run_spacing=8,
                            controls=[
                                ft.Button(
                                    content="Escolher foto",
                                    icon=ft.Icons.ADD_A_PHOTO_OUTLINED,
                                    tooltip="Adicionar uma foto PNG, JPG ou WEBP de até 2 MB",
                                    on_click=on_select_profile_photo,
                                ),
                                remove_photo_button,
                                ft.Button(
                                    content="Guia de uso",
                                    icon=ft.Icons.HELP_OUTLINE,
                                    on_click=lambda _event: on_help(),
                                ),
                                *(
                                    [
                                        ft.Button(
                                            content="Gerenciar usuários",
                                            icon=ft.Icons.GROUPS,
                                            on_click=lambda _event: on_manage_users(),
                                        )
                                    ]
                                    if on_manage_users is not None
                                    else []
                                ),
                                password_button,
                                *(
                                    [recovery_button]
                                    if on_rotate_administrator_recovery is not None
                                    else []
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            *(
                [
                    ft.Container(
                        bgcolor=AppColors.SURFACE,
                        border_radius=16,
                        padding=22,
                        content=ft.Column(
                            spacing=12,
                            controls=[
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    wrap=True,
                                    run_spacing=8,
                                    controls=[
                                        ft.Column(
                                            spacing=3,
                                            controls=[
                                                ft.Text(
                                                    "Avisos por e-mail",
                                                    size=17,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                ft.Text(
                                                    "Envia lembretes para todos os usuários "
                                                    "ativos cadastrados.",
                                                    size=12,
                                                    color=AppColors.TEXT_SECONDARY,
                                                ),
                                            ],
                                        ),
                                        ft.Container(
                                            border_radius=18,
                                            bgcolor=(
                                                AppColors.PRIMARY_LIGHT
                                                if email_settings.is_configured
                                                else AppColors.WARNING_LIGHT
                                            ),
                                            padding=ft.Padding.symmetric(
                                                horizontal=12,
                                                vertical=6,
                                            ),
                                            content=ft.Text(
                                                (
                                                    "Configurado"
                                                    if email_settings.is_configured
                                                    else "Não configurado"
                                                ),
                                                weight=ft.FontWeight.BOLD,
                                                color=(
                                                    AppColors.PRIMARY
                                                    if email_settings.is_configured
                                                    else AppColors.WARNING
                                                ),
                                            ),
                                        ),
                                    ],
                                ),
                                ft.Text(
                                    (
                                        f"Remetente: {email_settings.sender}"
                                        if email_settings.sender
                                        else "Nenhum remetente definido."
                                    ),
                                    size=12,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                                ft.Text(
                                    f"Destinatários automáticos: {automatic_recipients}",
                                    size=12,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                                ft.Text(
                                    f"Destinatários do teste: {test_recipients_text}",
                                    size=11,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                                ft.Text(
                                    "O envio usa a mesma tarefa silenciosa dos avisos do "
                                    "Windows. Ative os avisos em segundo plano para que os "
                                    "e-mails sejam enviados automaticamente.",
                                    size=11,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                                ft.Row(
                                    wrap=True,
                                    controls=[
                                        email_button,
                                        ft.Button(
                                            content="Testar e-mail",
                                            icon=ft.Icons.SEND_OUTLINED,
                                            disabled=not email_settings.is_configured,
                                            on_click=lambda _event: on_test_email(),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    )
                ]
                if current_user.is_admin
                else []
            ),
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=16,
                padding=22,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    wrap=True,
                    run_spacing=8,
                    controls=[
                        ft.Column(
                            spacing=3,
                            controls=[
                                ft.Text(
                                    "Aparência",
                                    size=17,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    "A escolha fica salva neste computador.",
                                    size=12,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                        theme_switch,
                    ],
                ),
            ),
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=16,
                padding=22,
                content=ft.Column(
                    spacing=14,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            wrap=True,
                            run_spacing=8,
                            controls=[
                                ft.Column(
                                    spacing=3,
                                    controls=[
                                        ft.Text(
                                            "Avisos em segundo plano",
                                            size=17,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            "Verifica prazos a cada 5 minutos, mesmo com a janela "
                                            "principal fechada.",
                                            size=12,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                ),
                                ft.Container(
                                    border_radius=18,
                                    bgcolor=(
                                        AppColors.PRIMARY_LIGHT
                                        if notifications_enabled
                                        else AppColors.WARNING_LIGHT
                                    ),
                                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                                    content=ft.Text(
                                        status_text,
                                        weight=ft.FontWeight.BOLD,
                                        color=status_color,
                                    ),
                                ),
                            ],
                        ),
                        ft.Text(
                            f"Banco monitorado: {database_path}",
                            size=12,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        ft.Text(
                            "Última verificação: "
                            f"{format_datetime(notification_status.last_checked_at)}",
                            size=12,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        ft.Text(last_result, size=12, color=AppColors.TEXT_SECONDARY),
                        ft.Text(
                            (
                                "O servidor, os e-mails e os backups continuam sem login. "
                                "Os avisos visuais aparecem quando a sessão do Windows está "
                                "iniciada. As tarefas são gerenciadas pelo instalador."
                                if managed_server_mode
                                else "O computador precisa estar ligado e a sessão do Windows "
                                "iniciada. A tarefa chama diretamente o notificador sem abrir "
                                "CMD ou PowerShell."
                            ),
                            size=12,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        ft.Row(
                            wrap=True,
                            run_spacing=8,
                            controls=[
                                ft.Button(
                                    content="Testar notificação",
                                    icon=ft.Icons.NOTIFICATIONS,
                                    tooltip=(
                                        "No modo servidor, valide o toast com um prazo operacional."
                                        if managed_server_mode
                                        else "Exibir imediatamente um aviso de teste no Windows"
                                    ),
                                    disabled=managed_server_mode,
                                    on_click=lambda _event: on_test_notification(),
                                ),
                                ft.Button(
                                    content="Ativar avisos",
                                    icon=ft.Icons.NOTIFICATIONS_ACTIVE,
                                    disabled=notifications_enabled or managed_server_mode,
                                    bgcolor=AppColors.PRIMARY,
                                    color=AppColors.WHITE,
                                    on_click=lambda _event: on_enable_notifications(),
                                ),
                                disable_notifications_button,
                            ],
                        ),
                    ],
                ),
            ),
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=16,
                padding=22,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            wrap=True,
                            run_spacing=8,
                            controls=[
                                ft.Text(
                                    "Local dos dados",
                                    size=17,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Container(
                                    border_radius=18,
                                    bgcolor=AppColors.PRIMARY_LIGHT,
                                    padding=ft.Padding.symmetric(
                                        horizontal=12,
                                        vertical=6,
                                    ),
                                    content=ft.Text(
                                        "Conectado",
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.PRIMARY,
                                    ),
                                ),
                            ],
                        ),
                        ft.Text(
                            "Arquivo em uso pelo programa",
                            size=11,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        ft.Text(str(database_path), size=12, color=AppColors.TEXT_PRIMARY),
                        ft.Text(
                            "Todos os ensaios e atividades são lidos e salvos neste arquivo. "
                            "Ele permanece em disco local para evitar conflitos e corrupção "
                            "durante as gravações.",
                            size=12,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        ft.Container(
                            border_radius=12,
                            bgcolor=(
                                AppColors.PRIMARY_LIGHT
                                if backup_directory is not None
                                else AppColors.WARNING_LIGHT
                            ),
                            border=ft.Border.all(
                                1,
                                (
                                    AppColors.PRIMARY
                                    if backup_directory is not None
                                    else AppColors.WARNING
                                ),
                            ),
                            padding=12,
                            content=ft.Column(
                                spacing=4,
                                controls=[
                                    ft.Text(
                                        (
                                            "Cópia diária externa configurada"
                                            if backup_directory is not None
                                            else "Cópia externa ainda não configurada"
                                        ),
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                        color=(
                                            AppColors.PRIMARY
                                            if backup_directory is not None
                                            else AppColors.WARNING
                                        ),
                                    ),
                                    ft.Text(
                                        (
                                            str(backup_directory)
                                            if backup_directory is not None
                                            else (
                                                "O sistema mantém os backups locais, mas uma "
                                                "falha do computador ainda pode afetar todas "
                                                "as cópias. Configure o OneDrive na instalação."
                                            )
                                        ),
                                        size=11,
                                        color=AppColors.TEXT_PRIMARY,
                                    ),
                                ],
                            ),
                        ),
                        ft.Row(
                            wrap=True,
                            run_spacing=8,
                            controls=[
                                ft.Button(
                                    content="Abrir pasta",
                                    icon=ft.Icons.FOLDER_OPEN,
                                    on_click=lambda _event: on_open_data_folder(),
                                ),
                                ft.Button(
                                    content="Criar cópia de segurança",
                                    icon=ft.Icons.BACKUP,
                                    on_click=on_backup,
                                ),
                                *(
                                    [
                                        ft.Button(
                                            content="Alterar pasta de backup",
                                            icon=ft.Icons.FOLDER_OPEN,
                                            on_click=on_configure_backup,
                                        )
                                    ]
                                    if on_configure_backup is not None
                                    else []
                                ),
                            ],
                        ),
                        ft.Text(
                            "Proteção automática: uma cópia local por dia na subpasta "
                            "“backups” e, quando configurado, outro backup diário no OneDrive. "
                            "Cada local mantém as 30 cópias mais recentes. Toda cópia automática "
                            "é verificada e recebe um manifesto de integridade SHA-256.",
                            size=11,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
            ),
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=16,
                padding=22,
                content=ft.Column(
                    spacing=12,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            wrap=True,
                            run_spacing=8,
                            controls=[
                                ft.Column(
                                    spacing=3,
                                    controls=[
                                        ft.Text(
                                            "Falhas do sistema e ações corretivas",
                                            size=17,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            "Registro exigido para avaliar impacto, conter a "
                                            "falha e demonstrar o tratamento adotado.",
                                            size=12,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                ),
                                report_incident_button,
                            ],
                        ),
                        dialog_banner(
                            "Relacionado à ABNT NBR ISO/IEC 17025:2017, itens 7.10, "
                            "7.11.3 e 8.7. O registro no software não substitui o procedimento "
                            "do laboratório para trabalho não conforme."
                        ),
                        *(
                            [incident_control(incident) for incident in system_incidents]
                            if system_incidents
                            else [
                                ft.Container(
                                    border_radius=12,
                                    bgcolor=AppColors.PAGE_BACKGROUND,
                                    padding=14,
                                    content=ft.Text(
                                        (
                                            "Nenhuma falha registrada. Isso não dispensa o "
                                            "relato quando ocorrer indisponibilidade, erro, "
                                            "perda ou risco "
                                            "à integridade dos dados."
                                            if current_user.is_admin
                                            else (
                                                "O histórico de falhas é reservado "
                                                "à administração. Você pode registrar "
                                                "um novo relato pelo botão acima."
                                            )
                                        ),
                                        size=11,
                                        color=AppColors.TEXT_SECONDARY,
                                    ),
                                )
                            ]
                        ),
                    ],
                ),
            ),
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=16,
                padding=22,
                content=ft.Column(
                    spacing=12,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            wrap=True,
                            run_spacing=8,
                            controls=[
                                ft.Column(
                                    spacing=3,
                                    controls=[
                                        ft.Text(
                                            "Conformidade normativa e validação",
                                            size=17,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            "Base considerada no projeto do ClimateTest Manager.",
                                            size=12,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                ),
                                ft.Container(
                                    border_radius=18,
                                    bgcolor=AppColors.PRIMARY_LIGHT,
                                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                                    content=ft.Text(
                                        "APOIO À CONFORMIDADE",
                                        size=10,
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.PRIMARY,
                                    ),
                                ),
                            ],
                        ),
                        ft.Container(
                            border_radius=12,
                            border=ft.Border.all(1, AppColors.DIVIDER),
                            padding=14,
                            content=ft.Column(
                                spacing=6,
                                controls=[
                                    ft.Text(
                                        "Normas diretamente aplicadas",
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        "• ABNT NBR ISO/IEC 17025:2017 — competência, registros "
                                        "técnicos, dados, sistemas de informação e gestão.\n"
                                        "• ABNT NBR IEC 60079-0:2020 — condições da Tabela 17 "
                                        "usadas no cálculo do ensaio climático.",
                                        size=11,
                                        color=AppColors.TEXT_SECONDARY,
                                        selectable=True,
                                    ),
                                ],
                            ),
                        ),
                        ft.ExpansionTile(
                            title=ft.Text(
                                "Referências complementares consideradas",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                            ),
                            subtitle=ft.Text(
                                "Segurança, ciclo de vida, qualidade e auditoria",
                                size=10,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                            controls=[
                                ft.Container(
                                    padding=ft.Padding.only(left=14, right=14, bottom=12),
                                    content=ft.Text(
                                        "EUROLAB Technical Report 01/2024; ISO/IEC 27001:2022; "
                                        "ISO/IEC 27002:2022; ISO/IEC/IEEE 12207:2026; "
                                        "ISO/IEC 25010:2023; ISO 19011:2026. Essas referências "
                                        "orientam controles, mas não são apresentadas como "
                                        "certificações do aplicativo.",
                                        size=11,
                                        color=AppColors.TEXT_SECONDARY,
                                        selectable=True,
                                    ),
                                )
                            ],
                        ),
                        ft.Text(
                            f"Versão do software: {__version__}  •  Esquema do banco: "
                            f"{SCHEMA_VERSION}  •  Regra: {NORMATIVE_RULE_VERSION}",
                            size=10,
                            color=AppColors.TEXT_SECONDARY,
                            selectable=True,
                        ),
                        ft.Container(
                            border_radius=12,
                            bgcolor=AppColors.WARNING_LIGHT,
                            padding=12,
                            content=ft.Text(
                                "Importante: o software foi projetado para apoiar os requisitos. "
                                "A conformidade e a acreditação pertencem ao laboratório e exigem "
                                "validação local, procedimentos aprovados, usuários competentes, "
                                "infraestrutura segura, auditorias e evidências de uso.",
                                size=11,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                        ),
                    ],
                ),
            ),
            ft.Container(
                bgcolor=AppColors.INFO_LIGHT,
                border_radius=12,
                padding=14,
                content=ft.Text(
                    "A Agenda interna é a referência do sistema para retiradas e limites "
                    "dos ensaios ativos. Não é necessária integração com Outlook ou outro "
                    "calendário externo.",
                    size=12,
                    color=AppColors.TEXT_PRIMARY,
                ),
            ),
        ],
    )
