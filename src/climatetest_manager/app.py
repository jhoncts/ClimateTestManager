"""Configuração da janela principal da aplicação."""

import asyncio
import ipaddress
import os
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from threading import Lock

import flet as ft
from sqlalchemy import Engine

from climatetest_manager import __version__
from climatetest_manager.config import (
    EmailSettings,
    get_database_path,
    get_default_data_directory,
    get_external_backup_directory,
    load_email_settings,
    load_remembered_session_token,
    load_theme_mode,
    normalize_smtp_password,
    save_email_settings,
    save_remembered_session_token,
    save_storage_settings,
    save_theme_mode,
    storage_setup_required,
    suggest_onedrive_backup_directory,
    test_controls_enabled,
)
from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.domain.incidents import incident_reason
from climatetest_manager.repositories.climate_tests import (
    ClimateTestRepository,
    UserNotificationSummary,
)
from climatetest_manager.repositories.users import UserRepository
from climatetest_manager.services.auth import (
    AuthenticationService,
    UserRegistrationCommand,
    UserSummary,
    UserUpdateCommand,
)
from climatetest_manager.services.background import (
    configure_notification_task,
    notification_task_installed,
)
from climatetest_manager.services.climate_tests import (
    ClimateTestListItem,
    ClimateTestService,
    CreateClimateTestCommand,
    UpdateClimateTestCommand,
)
from climatetest_manager.services.exports import (
    build_database_backup_bytes,
    build_tests_csv_bytes,
    create_configured_database_backups,
)
from climatetest_manager.services.notifications import (
    EmailDeliveryReceipt,
    EmailNotificationProvider,
    WindowsToastProvider,
    deliver_pending_incident_emails,
)
from climatetest_manager.ui.components import (
    dialog_actions,
    dialog_banner,
    github_credit,
    styled_dialog,
    user_avatar,
)
from climatetest_manager.ui.responsive import (
    RESIZE_REBUILD_MIN_DELTA,
    LayoutProfile,
    viewport_width,
)
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.ui.views.agenda import build_agenda_view
from climatetest_manager.ui.views.auth import (
    build_initial_setup_view,
    build_login_view,
    build_server_waiting_view,
    build_storage_setup_view,
)
from climatetest_manager.ui.views.dashboard import build_dashboard
from climatetest_manager.ui.views.history import build_history_view
from climatetest_manager.ui.views.new_test import (
    NewTestDraft,
    NewTestView,
    build_edit_test_view,
)
from climatetest_manager.ui.views.notifications import build_notifications_view
from climatetest_manager.ui.views.onboarding import build_onboarding_view
from climatetest_manager.ui.views.settings import build_settings_view
from climatetest_manager.ui.views.test_details import build_test_details_view
from climatetest_manager.ui.views.tests_list import build_tests_list_view
from climatetest_manager.ui.views.users import build_users_view

_SERVER_CONTEXT_LOCK = Lock()
_INCIDENT_EMAIL_LOCK = Lock()
_SERVER_ENGINE: Engine | None = None
_SERVER_REPOSITORY: ClimateTestRepository | None = None
_SERVER_AUTH_SERVICE: AuthenticationService | None = None


def _server_mode() -> bool:
    return os.getenv("CLIMATETEST_SERVER_MODE", "").strip() == "1"


def _local_server_client(page: ft.Page) -> bool:
    """Reconhece o navegador local; conexões remotas não recebem o assistente inicial."""

    if not _server_mode():
        return True
    raw_ip = str(getattr(page, "client_ip", "") or "").strip()
    if not raw_ip:
        return False
    if raw_ip.casefold() == "localhost":
        return True
    with suppress(ValueError):
        address = ipaddress.ip_address(raw_ip)
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
            address = address.ipv4_mapped
        return address.is_loopback
    return False


def _application_theme() -> ft.Theme:
    """Usa tipografia nativa do Windows e rolagem discreta."""

    return ft.Theme(
        color_scheme_seed=AppColors.PRIMARY,
        font_family="Segoe UI",
        visual_density=ft.VisualDensity.COMFORTABLE,
        scrollbar_theme=ft.ScrollbarTheme(
            thumb_visibility=False,
            track_visibility=False,
            thickness=6,
            radius=8,
            thumb_color=AppColors.TEXT_SECONDARY,
            cross_axis_margin=4,
            main_axis_margin=8,
        ),
    )


def _screen_switcher() -> ft.AnimatedSwitcher:
    """Mantém uma superfície estável, sem flashes de opacidade entre telas."""

    return ft.AnimatedSwitcher(
        content=ft.Container(expand=True),
        duration=0,
        reverse_duration=0,
        transition=ft.AnimatedSwitcherTransition.FADE,
        expand=True,
    )


def _navigation_item(
    label: str,
    icon: ft.IconData,
    *,
    selected: bool = False,
    on_click: Callable[[], None] | None = None,
    layout: LayoutProfile,
    badge_count: int = 0,
) -> ft.Container:
    """Cria um item visual da navegação lateral."""

    text_controls: list[ft.Control] = []
    if not layout.compact_navigation:
        text_controls.append(
            ft.Text(
                label,
                size=14,
                weight=ft.FontWeight.BOLD if selected else ft.FontWeight.NORMAL,
                color=AppColors.PRIMARY if selected else AppColors.NAV_TEXT,
            )
        )
    return ft.Container(
        border_radius=10,
        bgcolor=AppColors.NAV_SELECTED if selected else AppColors.NAV_BACKGROUND,
        padding=10 if layout.compact_navigation else 12,
        alignment=ft.Alignment.CENTER if layout.compact_navigation else None,
        tooltip=label if layout.compact_navigation else None,
        opacity=1 if on_click or selected else 0.55,
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
            alignment=(
                ft.MainAxisAlignment.CENTER
                if layout.compact_navigation
                else ft.MainAxisAlignment.START
            ),
            spacing=0 if layout.compact_navigation else 12,
            controls=[
                ft.Icon(
                    icon,
                    size=layout.navigation_icon_size,
                    color=AppColors.PRIMARY if selected else AppColors.NAV_TEXT,
                ),
                *text_controls,
            ],
        ),
    )


def _build_sidebar(
    *,
    selected_view: str,
    on_dashboard: Callable[[], None],
    on_tests: Callable[[], None],
    on_new_test: Callable[[], None],
    on_agenda: Callable[[], None],
    on_history: Callable[[], None],
    on_notifications: Callable[[], None],
    on_help: Callable[[], None],
    on_settings: Callable[[], None],
    on_users: Callable[[], None] | None,
    on_logout: Callable[[], None],
    on_github: Callable[[], None],
    on_toggle_sidebar: Callable[[], None] | None,
    current_user: UserSummary,
    layout: LayoutProfile,
    notification_count: int,
) -> ft.Container:
    """Monta a identidade e a navegação principal."""

    brand_icon = ft.Container(
        width=layout.brand_icon_size,
        height=layout.brand_icon_size,
        border_radius=12,
        bgcolor=AppColors.SURFACE,
        padding=3,
        alignment=ft.Alignment.CENTER,
        content=ft.Image(
            src="brand/climatetest-logo.png",
            fit=ft.BoxFit.CONTAIN,
            semantics_label="Logo do ClimateTest Manager",
        ),
    )
    brand: ft.Control
    if layout.compact_navigation:
        brand = ft.Column(
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    tooltip="ClimateTest Manager",
                    content=brand_icon,
                ),
                *(
                    [
                        ft.IconButton(
                            icon=ft.Icons.KEYBOARD_DOUBLE_ARROW_RIGHT,
                            tooltip="Expandir menu lateral",
                            icon_size=20,
                            on_click=lambda _event: on_toggle_sidebar(),
                        )
                    ]
                    if on_toggle_sidebar is not None
                    else []
                ),
            ],
        )
    else:
        brand = ft.Row(
            spacing=12,
            controls=[
                brand_icon,
                ft.Column(
                    spacing=0,
                    controls=[
                        ft.Text(
                            "ClimateTest",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                        ft.Text(
                            "Manager",
                            size=13,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
                ft.Container(expand=True),
                *(
                    [
                        ft.IconButton(
                            icon=ft.Icons.KEYBOARD_DOUBLE_ARROW_LEFT,
                            tooltip="Recolher menu lateral",
                            icon_size=20,
                            on_click=lambda _event: on_toggle_sidebar(),
                        )
                    ]
                    if on_toggle_sidebar is not None
                    else []
                ),
            ],
        )

    if layout.compact_navigation:
        account: ft.Control = ft.Column(
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    tooltip=f"{current_user.full_name} • {current_user.role_label}",
                    content=user_avatar(current_user, size=34),
                ),
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    tooltip="Sair da conta",
                    icon_size=18,
                    on_click=lambda _event: on_logout(),
                ),
            ],
        )
        footer: list[ft.Control] = [
            ft.Divider(height=1, color=AppColors.DIVIDER),
            github_credit(lambda _event: on_github(), compact=True),
        ]
    else:
        account = ft.Row(
            spacing=10,
            controls=[
                user_avatar(current_user, size=36),
                ft.Column(
                    expand=True,
                    spacing=1,
                    controls=[
                        ft.Text(
                            current_user.full_name,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                        ft.Text(
                            current_user.role_label,
                            size=10,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    tooltip="Sair da conta",
                    icon_size=18,
                    on_click=lambda _event: on_logout(),
                ),
            ],
        )
        footer = [
            ft.Divider(height=1, color=AppColors.DIVIDER),
            ft.Text(
                "IEC 60079-0 + ISO/IEC 17025",
                size=11,
                color=AppColors.TEXT_SECONDARY,
            ),
            ft.Text(
                f"Versão {__version__}",
                size=11,
                color=AppColors.TEXT_SECONDARY,
            ),
            github_credit(lambda _event: on_github()),
        ]

    return ft.Container(
        width=layout.sidebar_width,
        bgcolor=AppColors.NAV_BACKGROUND,
        padding=layout.sidebar_padding,
        content=ft.Column(
            spacing=8,
            controls=[
                brand,
                ft.Container(height=16 if layout.compact_navigation else 22),
                _navigation_item(
                    "Dashboard",
                    ft.Icons.DASHBOARD,
                    selected=selected_view == "dashboard",
                    on_click=on_dashboard,
                    layout=layout,
                ),
                _navigation_item(
                    "Ensaios",
                    ft.Icons.LIST,
                    selected=selected_view in {"tests", "details"},
                    on_click=on_tests,
                    layout=layout,
                ),
                _navigation_item(
                    "Novo ensaio",
                    ft.Icons.ADD,
                    selected=selected_view == "new_test",
                    on_click=on_new_test,
                    layout=layout,
                ),
                _navigation_item(
                    "Agenda",
                    ft.Icons.CALENDAR_MONTH,
                    selected=selected_view == "agenda",
                    on_click=on_agenda,
                    layout=layout,
                ),
                _navigation_item(
                    "Atividades",
                    ft.Icons.HISTORY,
                    selected=selected_view == "history",
                    on_click=on_history,
                    layout=layout,
                ),
                _navigation_item(
                    "Notificações",
                    ft.Icons.NOTIFICATIONS_OUTLINED,
                    selected=selected_view == "notifications",
                    on_click=on_notifications,
                    layout=layout,
                    badge_count=notification_count,
                ),
                _navigation_item(
                    "Guia de uso",
                    ft.Icons.HELP_OUTLINE,
                    selected=selected_view == "help",
                    on_click=on_help,
                    layout=layout,
                ),
                _navigation_item(
                    "Configurações",
                    ft.Icons.SETTINGS,
                    selected=selected_view == "settings",
                    on_click=on_settings,
                    layout=layout,
                ),
                *(
                    [
                        _navigation_item(
                            "Usuários",
                            ft.Icons.GROUPS,
                            selected=selected_view == "users",
                            on_click=on_users,
                            layout=layout,
                        )
                    ]
                    if on_users is not None
                    else []
                ),
                ft.Container(expand=True),
                ft.Divider(height=1, color=AppColors.DIVIDER),
                account,
                *footer,
            ],
        ),
    )


def _build_shell(
    content: ft.Control,
    *,
    selected_view: str,
    on_dashboard: Callable[[], None],
    on_tests: Callable[[], None],
    on_new_test: Callable[[], None],
    on_agenda: Callable[[], None],
    on_history: Callable[[], None],
    on_notifications: Callable[[], None],
    on_help: Callable[[], None],
    on_settings: Callable[[], None],
    on_users: Callable[[], None] | None,
    on_logout: Callable[[], None],
    on_github: Callable[[], None],
    on_toggle_sidebar: Callable[[], None] | None,
    current_user: UserSummary,
    layout: LayoutProfile,
    notification_count: int,
) -> ft.Row:
    """Combina a navegação e o conteúdo da tela atual."""

    return ft.Row(
        expand=True,
        spacing=0,
        controls=[
            _build_sidebar(
                selected_view=selected_view,
                on_dashboard=on_dashboard,
                on_tests=on_tests,
                on_new_test=on_new_test,
                on_agenda=on_agenda,
                on_history=on_history,
                on_notifications=on_notifications,
                on_help=on_help,
                on_settings=on_settings,
                on_users=on_users,
                on_logout=on_logout,
                on_github=on_github,
                on_toggle_sidebar=on_toggle_sidebar,
                current_user=current_user,
                layout=layout,
                notification_count=notification_count,
            ),
            ft.Container(
                expand=True,
                bgcolor=AppColors.PAGE_BACKGROUND,
                padding=layout.content_padding,
                content=content,
            ),
        ],
    )


class ClimateTestApplication:
    """Controla navegação e casos de uso sem colocar regras na interface."""

    def __init__(
        self,
        page: ft.Page,
        repository: ClimateTestRepository,
        *,
        auth_service: AuthenticationService,
        current_user: UserSummary,
        session_token: str | None,
        theme_mode: str,
        on_signed_out: Callable[[], None],
        host_switcher: ft.AnimatedSwitcher | None = None,
        host_mounted: bool = False,
    ) -> None:
        self._page = page
        self._repository = repository
        self._auth_service = auth_service
        self._current_user = current_user
        self._session_token = session_token
        self._theme_mode = theme_mode
        self._on_signed_out = on_signed_out
        self._service = ClimateTestService(
            repository,
            actor_provider=lambda: self._current_user.actor_label,
        )
        self._selected_view: str | None = None
        self._new_test_view: NewTestView | None = None
        self._new_test_draft: NewTestDraft | None = None
        self._transition_index = 0
        self._shell_mounted = host_mounted
        self._switcher = host_switcher or _screen_switcher()
        initial_width = viewport_width(page)
        self._layout = LayoutProfile.from_width(initial_width)
        self._sidebar_collapsed = False
        self._layout_anchor_width = initial_width
        self._current_content: ft.Control | None = None
        self._screen_container: ft.Container | None = None
        self._scroll_offset = 0.0
        self._page.on_resize = self._handle_resize

    def start(self) -> None:
        if self._current_user.onboarding_completed:
            self.show_dashboard()
        else:
            self.show_help(first_access=True)

    def _render(self, content: ft.Control, *, selected_view: str) -> None:
        if (
            self._selected_view == "new_test"
            and selected_view != "new_test"
            and self._new_test_view is not None
        ):
            self._new_test_draft = self._new_test_view.snapshot_draft()
        self._scroll_offset = 0.0
        self._bind_scroll_state(content)
        self._transition_index += 1
        self._current_content = content
        self._selected_view = selected_view
        shell = self._build_current_shell()
        animated_content = ft.Container(
            key=f"{selected_view}-{self._transition_index}",
            expand=True,
            content=shell,
        )
        self._screen_container = animated_content
        if not self._shell_mounted:
            self._page.clean()
            self._page.add(self._switcher)
            self._shell_mounted = True
        self._switcher.content = animated_content
        self._page.update()

    def _build_current_shell(self) -> ft.Row:
        """Reconstrói apenas a moldura, preservando o estado da tela aberta."""

        if self._current_content is None or self._selected_view is None:
            raise RuntimeError("Não há tela selecionada para compor o shell.")
        effective_layout = self._layout.with_collapsed_sidebar(self._sidebar_collapsed)
        notification_count = sum(
            not notification.is_read
            for notification in self._repository.list_user_notifications(
                user_id=self._current_user.id,
                is_admin=self._current_user.is_admin,
            )
        )
        return _build_shell(
            self._current_content,
            selected_view=self._selected_view,
            on_dashboard=self.show_dashboard,
            on_tests=self.show_tests,
            on_new_test=self.show_new_test,
            on_agenda=self.show_agenda,
            on_history=self.show_history,
            on_notifications=self.show_notifications,
            on_help=self.show_help,
            on_settings=self.show_settings,
            on_users=self.show_users if self._current_user.is_admin else None,
            on_logout=self._confirm_logout,
            on_github=self._open_github,
            on_toggle_sidebar=(self._toggle_sidebar if self._layout.mode != "compact" else None),
            current_user=self._current_user,
            layout=effective_layout,
            notification_count=notification_count,
        )

    def _toggle_sidebar(self) -> None:
        """Recolhe ou expande o menu sem reconstruir o conteúdo da tela."""

        if self._layout.mode == "compact":
            return
        self._sidebar_collapsed = not self._sidebar_collapsed
        if self._screen_container is None or self._current_content is None:
            return
        self._screen_container.content = self._build_current_shell()
        with suppress(RuntimeError):
            self._screen_container.update()
        self._restore_scroll_position()

    def _handle_resize(self, event: object | None = None) -> None:
        """Alterna a moldura somente quando a janela cruza um breakpoint."""

        next_width = viewport_width(self._page, event)
        next_layout = LayoutProfile.stable_from_width(
            next_width,
            current_mode=self._layout.mode,
        )
        if next_layout.mode == self._layout.mode:
            return
        if abs(next_width - self._layout_anchor_width) < RESIZE_REBUILD_MIN_DELTA:
            return
        self._layout = next_layout
        self._layout_anchor_width = next_width
        if self._screen_container is None or self._current_content is None:
            return
        self._screen_container.content = self._build_current_shell()
        with suppress(RuntimeError):
            self._screen_container.update()
        self._restore_scroll_position()

    def _bind_scroll_state(self, content: ft.Control) -> None:
        """Guarda a posição das telas roláveis sem provocar atualizações visuais."""

        if not isinstance(content, ft.ScrollableControl):
            return
        content.scroll_interval = 50
        content.on_scroll = self._remember_scroll_position

    def _remember_scroll_position(self, event: object) -> None:
        pixels = getattr(event, "pixels", None)
        if isinstance(pixels, (int, float)):
            self._scroll_offset = max(0.0, float(pixels))

    def _restore_scroll_position(self) -> None:
        """Restaura o ponto lido antes de uma troca responsiva da moldura."""

        if self._scroll_offset <= 0 or not isinstance(
            self._current_content,
            ft.ScrollableControl,
        ):
            return
        run_task = getattr(self._page, "run_task", None)
        if callable(run_task):
            run_task(
                self._current_content.scroll_to,
                offset=self._scroll_offset,
                duration=0,
            )

    def show_dashboard(self) -> None:
        content = build_dashboard(
            self._service.dashboard_summary(),
            self._service.list_dashboard_tests(),
            self._service.resource_statuses(),
            on_new_test=self.show_new_test,
            on_select=self.show_details,
            on_pause_resource=self._pause_resource,
            on_resume_resource=self._resume_resource,
        )
        self._render(content, selected_view="dashboard")

    def show_new_test(self) -> None:
        if self._selected_view == "new_test" and self._new_test_view is not None:
            return
        self._new_test_view = NewTestView(
            on_cancel=self._confirm_discard_new_test,
            on_save=self._save_test,
            draft=self._new_test_draft,
        )
        self._render(self._new_test_view.root, selected_view="new_test")

    def _confirm_discard_new_test(self) -> None:
        page = self._page

        def confirm(_event: object | None = None) -> None:
            page.pop_dialog()
            self._discard_new_test()

        page.show_dialog(
            styled_dialog(
                title="Descartar o novo ensaio?",
                subtitle="Os dados ainda não foram salvos",
                icon=ft.Icons.DELETE_SWEEP_OUTLINED,
                danger=True,
                content=ft.Container(
                    width=500,
                    content=dialog_banner(
                        "O preenchimento atual será apagado. Escolha “Continuar preenchendo” "
                        "para voltar ao formulário sem perder os dados.",
                        icon=ft.Icons.WARNING_AMBER,
                        danger=True,
                    ),
                ),
                actions=dialog_actions(
                    page=page,
                    primary_label="Descartar preenchimento",
                    primary_icon=ft.Icons.DELETE_SWEEP_OUTLINED,
                    on_confirm=confirm,
                    danger=True,
                    cancel_label="Continuar preenchendo",
                ),
            )
        )

    def _discard_new_test(self) -> None:
        self._new_test_view = None
        self._new_test_draft = None
        self.show_dashboard()

    def show_edit_test(self, test_id: int) -> None:
        content = build_edit_test_view(
            self._service.get_details(test_id),
            on_cancel=lambda: self.show_details(test_id),
            on_save=lambda command: self._update_test(test_id, command),
        )
        self._render(content, selected_view="details")

    def show_tests(self) -> None:
        content = build_tests_list_view(
            self._service.list_tests(),
            on_select=self.show_details,
            on_new_test=self.show_new_test,
            on_export=self._export_csv,
        )
        self._render(content, selected_view="tests")

    def show_history(self) -> None:
        content = build_history_view(
            self._service.list_history(),
            on_select=self.show_details,
        )
        self._render(content, selected_view="history")

    def show_notifications(self) -> None:
        notifications = self._repository.list_user_notifications(
            user_id=self._current_user.id,
            is_admin=self._current_user.is_admin,
        )
        content = build_notifications_view(
            notifications,
            is_admin=self._current_user.is_admin,
            on_mark_read=self._mark_notification_read,
            on_mark_all_read=lambda: self._mark_all_notifications_read(notifications),
        )
        self._render(content, selected_view="notifications")

    def _mark_notification_read(self, source_kind: str, source_id: int) -> None:
        self._repository.mark_user_notification_read(
            user_id=self._current_user.id,
            source_kind=source_kind,
            source_id=source_id,
        )
        self.show_notifications()

    def _mark_all_notifications_read(
        self,
        notifications: list[UserNotificationSummary],
    ) -> None:
        for notification in notifications:
            if not notification.is_read:
                self._repository.mark_user_notification_read(
                    user_id=self._current_user.id,
                    source_kind=notification.source_kind,
                    source_id=notification.source_id,
                )
        self.show_notifications()

    def show_agenda(self) -> None:
        content = build_agenda_view(
            self._service.list_agenda_events(),
            on_select=self.show_details,
        )
        self._render(content, selected_view="agenda")

    def show_settings(self) -> None:
        content = build_settings_view(
            database_path=get_database_path(),
            backup_directory=get_external_backup_directory(),
            notifications_enabled=notification_task_installed(),
            notification_status=self._service.notification_status(),
            email_settings=load_email_settings(),
            email_recipients=(
                self._auth_service.list_active_emails(self._current_user)
                if self._current_user.is_admin
                else []
            ),
            system_incidents=(
                self._repository.list_system_incidents() if self._current_user.is_admin else []
            ),
            theme_mode=self._theme_mode,
            current_user=self._current_user,
            on_theme_change=self._change_theme,
            on_change_password=self._change_password,
            on_manage_users=self.show_users if self._current_user.is_admin else None,
            on_help=self.show_help,
            on_enable_notifications=lambda: self._configure_notifications(True),
            on_disable_notifications=lambda: self._configure_notifications(False),
            on_test_notification=self._test_notification,
            on_save_email_settings=self._save_email_settings,
            on_test_email=self._test_email,
            on_select_profile_photo=self._select_profile_photo,
            on_remove_profile_photo=self._remove_profile_photo,
            on_open_data_folder=self._open_data_folder,
            on_backup=self._backup_database,
            on_configure_backup=(
                self._configure_backup_directory if self._current_user.is_admin else None
            ),
            on_report_system_incident=self._report_system_incident,
            on_resolve_system_incident=(
                self._resolve_system_incident if self._current_user.is_admin else None
            ),
            on_refresh=self.show_settings,
            on_rotate_administrator_recovery=(
                self._rotate_administrator_recovery_code
                if self._current_user.is_admin and _local_server_client(self._page)
                else None
            ),
            allow_theme_change=not _server_mode(),
            managed_server_mode=_server_mode(),
        )
        self._render(content, selected_view="settings")

    def _report_system_incident(
        self,
        reason_code: str,
        description: str,
        immediate_action: str,
    ) -> str | None:
        """Persiste a falha imediatamente; alertas externos são processados em segundo plano."""

        if not self._current_user.can_operate:
            return "Este perfil possui acesso somente para consulta."
        try:
            reason = incident_reason(reason_code)
        except ValueError as error:
            return str(error)
        if not 10 <= len(description) <= 2000:
            return "A descrição precisa ter entre 10 e 2.000 caracteres."
        if not 10 <= len(immediate_action) <= 2000:
            return "A ação imediata precisa ter entre 10 e 2.000 caracteres."
        try:
            self._repository.report_system_incident(
                reason_code=reason.code,
                category=reason.label,
                severity=reason.severity,
                description=description,
                immediate_action=immediate_action,
                reported_by=self._current_user.actor_label,
            )
            self._page.run_task(self._deliver_incident_email_queue)
        except (OSError, ValueError) as error:
            return str(error)
        return None

    async def _deliver_incident_email_queue(self) -> None:
        """Tenta o e-mail logo após o registro sem bloquear a janela do operador."""

        try:
            await asyncio.to_thread(self._deliver_incident_email_queue_sync)
        except Exception:
            # A tarefa agendada continua sendo a retentativa auditável.
            return

    def _deliver_incident_email_queue_sync(self) -> None:
        with _INCIDENT_EMAIL_LOCK:
            settings = load_email_settings()
            if not settings.automatic_enabled:
                return
            recipients = self._auth_service.notification_admin_emails()
            if not recipients:
                return
            deliver_pending_incident_emails(
                self._repository,
                EmailNotificationProvider(settings, recipients),
            )

    def _resolve_system_incident(
        self,
        incident_id: int,
        corrective_action: str,
    ) -> str | None:
        """Permite que somente o administrador encerre uma falha tratada."""

        if not self._current_user.is_admin:
            return "Somente administradores podem encerrar uma falha."
        if not 15 <= len(corrective_action) <= 3000:
            return "A ação corretiva precisa ter entre 15 e 3.000 caracteres."
        try:
            self._repository.resolve_system_incident(
                incident_id,
                corrective_action=corrective_action,
                resolved_by=self._current_user.actor_label,
            )
        except (LookupError, ValueError) as error:
            return str(error)
        self._show_message("Falha encerrada com a ação corretiva registrada.")
        return None

    def _rotate_administrator_recovery_code(self) -> str:
        if not self._current_user.is_admin or not _local_server_client(self._page):
            raise ValueError(
                "O código só pode ser renovado por um administrador no próprio servidor."
            )
        return self._auth_service.rotate_administrator_recovery_code(self._current_user)

    def show_help(self, *, first_access: bool = False) -> None:
        content = build_onboarding_view(
            user_name=self._current_user.first_name,
            on_complete=(self._complete_onboarding if first_access else self.show_dashboard),
            first_access=first_access,
        )
        self._render(content, selected_view="help")

    def _complete_onboarding(self) -> None:
        try:
            self._current_user = self._auth_service.complete_onboarding(self._current_user)
        except ValueError as error:
            self._show_message(str(error), error=True)
            return
        self.show_dashboard()
        self._show_message("Configuração inicial concluída.")

    def show_users(self) -> None:
        if not self._current_user.is_admin:
            self._show_message(
                "Somente administradores podem gerenciar usuários.",
                error=True,
            )
            return
        content = build_users_view(
            self._auth_service.list_users(self._current_user),
            current_user=self._current_user,
            on_create=self._create_user,
            on_update=self._update_user,
            on_reset_password=self._reset_user_password,
        )
        self._render(content, selected_view="users")

    def _create_user(self, command: UserRegistrationCommand) -> str | None:
        try:
            self._auth_service.create_user(self._current_user, command)
        except ValueError as error:
            return str(error)
        self.show_users()
        return None

    def _update_user(self, user_id: int, command: UserUpdateCommand) -> str | None:
        try:
            updated = self._auth_service.update_user(
                self._current_user,
                user_id,
                command,
            )
        except ValueError as error:
            return str(error)
        if user_id == self._current_user.id:
            self._current_user = updated
        self.show_users() if self._current_user.is_admin else self.show_dashboard()
        return None

    def _reset_user_password(
        self,
        user_id: int,
        password: str,
        confirmation: str,
    ) -> str | None:
        try:
            self._auth_service.reset_password(
                self._current_user,
                user_id,
                password,
                confirmation,
            )
        except ValueError as error:
            return str(error)
        if user_id == self._current_user.id:
            self._finish_signed_out("Senha redefinida. Entre novamente com a nova senha.")
            return None
        self.show_users()
        return None

    def _change_password(
        self,
        current_password: str,
        new_password: str,
        confirmation: str,
    ) -> None:
        try:
            self._auth_service.change_own_password(
                self._current_user,
                current_password,
                new_password,
                confirmation,
            )
        except ValueError as error:
            self._show_message(str(error), error=True)
            return
        self._finish_signed_out("Senha alterada. Entre novamente com a nova senha.")

    def _logout(self) -> None:
        try:
            self._auth_service.logout(self._session_token, self._current_user)
        finally:
            self._finish_signed_out()

    def _confirm_logout(self) -> None:
        page = self._page

        def confirm(_event: object | None = None) -> None:
            page.pop_dialog()
            self._logout()

        page.show_dialog(
            styled_dialog(
                title="Sair da conta?",
                subtitle=f"Sessão de @{self._current_user.username}",
                icon=ft.Icons.LOGOUT,
                content=ft.Container(
                    width=460,
                    content=dialog_banner(
                        "Você voltará para a tela de login. Nenhum ensaio ou registro salvo "
                        "será apagado.",
                        icon=ft.Icons.INFO_OUTLINE,
                    ),
                ),
                actions=dialog_actions(
                    page=page,
                    primary_label="Sim, sair da conta",
                    primary_icon=ft.Icons.LOGOUT,
                    on_confirm=confirm,
                    cancel_label="Permanecer conectado",
                ),
            )
        )

    def _finish_signed_out(self, message: str | None = None) -> None:
        with suppress(OSError):
            save_remembered_session_token(None)
        self._session_token = None
        self._page.on_resize = None
        self._on_signed_out()
        if message:
            self._show_message(message)

    def show_details(self, test_id: int) -> None:
        details = self._service.get_details(test_id)
        content = build_test_details_view(
            details,
            on_back=self.show_tests,
            on_start_chamber=lambda value: self._perform(
                test_id,
                lambda: self._service.start_chamber(test_id, value),
                "Câmara iniciada e prazos calculados.",
            ),
            on_start_drying=lambda value: self._perform(
                test_id,
                lambda: self._service.start_drying(test_id, value),
                "Secagem iniciada a partir do horário real.",
            ),
            on_finish=lambda value: self._perform(
                test_id,
                lambda: self._service.finish(test_id, value),
                "Ensaio finalizado.",
            ),
            on_cancel=lambda reason: self._perform(
                test_id,
                lambda: self._service.cancel(test_id, reason),
                "Ensaio cancelado e motivo registrado.",
            ),
            on_edit=lambda: self.show_edit_test(test_id),
            on_delete=lambda: self._delete_test(test_id),
            on_change_timestamp=lambda timestamp, value, reason: self._perform(
                test_id,
                lambda: self._service.change_operational_timestamp(
                    test_id,
                    timestamp,
                    value,
                    reason,
                ),
                "Horário operacional corrigido e alteração registrada.",
            ),
            on_advance_for_testing=(
                (
                    lambda: self._perform(
                        test_id,
                        lambda: self._service.advance_for_testing(test_id),
                        "Etapa avançada somente para validação.",
                    )
                )
                if test_controls_enabled()
                else None
            ),
        )
        self._render(content, selected_view="details")

    def _save_test(self, command: CreateClimateTestCommand) -> None:
        test_id = self._service.create(command)
        self._new_test_view = None
        self._new_test_draft = None
        self.show_dashboard()
        self._page.show_dialog(
            ft.SnackBar(
                content=f"Ensaio #{test_id} cadastrado com sucesso.",
                bgcolor=AppColors.PRIMARY,
                show_close_icon=True,
            )
        )

    def _update_test(self, test_id: int, command: UpdateClimateTestCommand) -> None:
        try:
            self._service.update(test_id, command)
        except (ValueError, LookupError) as error:
            self._show_message(str(error), error=True)
            return
        self.show_details(test_id)
        self._show_message("Dados corrigidos e alteração registrada.")

    def _delete_test(self, test_id: int) -> None:
        try:
            self._service.delete_waiting(test_id)
        except (ValueError, LookupError) as error:
            self._show_message(str(error), error=True)
            return
        self.show_tests()
        self._show_message(f"Cadastro do ensaio #{test_id} excluído.")

    def _pause_resource(self, resource: str, reason: str) -> None:
        try:
            affected = self._service.pause_resource(resource, reason)
        except (ValueError, LookupError) as error:
            self._show_message(str(error), error=True)
            return
        self.show_dashboard()
        self._show_message(
            f"Equipamento pausado. {affected} ensaio(s) tiveram a contagem congelada."
        )

    def _resume_resource(self, resource: str) -> None:
        try:
            affected = self._service.resume_resource(resource)
        except (ValueError, LookupError) as error:
            self._show_message(str(error), error=True)
            return
        self.show_dashboard()
        self._show_message(f"Equipamento retomado. {affected} prazo(s) foram recalculados.")

    def _change_theme(self, mode: str) -> None:
        if _server_mode():
            self._show_message(
                "O modo servidor usa um tema único para manter todas as sessões consistentes."
            )
            return
        self._theme_mode = "dark" if mode == "dark" else "light"
        AppColors.apply_mode(self._theme_mode)
        self._page.theme_mode = (
            ft.ThemeMode.DARK if self._theme_mode == "dark" else ft.ThemeMode.LIGHT
        )
        self._page.theme = _application_theme()
        self._page.bgcolor = AppColors.PAGE_BACKGROUND
        try:
            save_theme_mode(self._theme_mode)
        except OSError as error:
            self._show_message(
                f"O tema foi alterado, mas não foi possível salvar a preferência: {error}",
                error=True,
            )
        self.show_settings()

    def _perform(
        self,
        test_id: int,
        operation: Callable[[], None],
        success_message: str,
    ) -> None:
        try:
            operation()
        except (ValueError, LookupError) as error:
            self._show_message(str(error), error=True)
            return
        self.show_details(test_id)
        self._show_message(success_message)

    def _show_message(self, message: str, *, error: bool = False) -> None:
        self._page.show_dialog(
            ft.SnackBar(
                content=message,
                bgcolor=AppColors.DANGER if error else AppColors.PRIMARY,
                show_close_icon=True,
            )
        )

    async def _export_csv(self, tests: list[ClimateTestListItem]) -> None:
        file_name = f"ensaios_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path = await ft.FilePicker().save_file(
            dialog_title="Escolha onde salvar a exportação dos ensaios",
            file_name=file_name,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["csv"],
            src_bytes=build_tests_csv_bytes(tests),
        )
        if path:
            self._show_message(f"CSV salvo com {len(tests)} ensaio(s) em: {path}")

    async def _backup_database(self, _event: object | None = None) -> None:
        database_path = get_database_path()
        try:
            backup_bytes = build_database_backup_bytes(database_path)
        except (OSError, ValueError) as error:
            self._show_message(str(error), error=True)
            return
        file_name = f"climatetest_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
        path = await ft.FilePicker().save_file(
            dialog_title="Escolha onde salvar a cópia de segurança",
            file_name=file_name,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["db"],
            src_bytes=backup_bytes,
        )
        if path:
            self._show_message(f"Cópia de segurança criada em: {path}")

    async def _configure_backup_directory(self, _event: object | None = None) -> None:
        if _server_mode():
            page = self._page
            path_field = ft.TextField(
                label="Pasta de backup no computador servidor",
                value=str(
                    get_external_backup_directory() or suggest_onedrive_backup_directory() or ""
                ),
                hint_text=(
                    "Ex.: C:\\Users\\Laboratorio\\OneDrive - Empresa\\ClimateTestManager\\Backups"
                ),
                max_length=500,
                counter="",
            )
            error_text = ft.Text("", size=11, color=AppColors.DANGER)

            def confirm(_confirm_event: object | None = None) -> None:
                if not path_field.value.strip():
                    error_text.value = "Informe a pasta de backup do servidor."
                    error_text.update()
                    return
                try:
                    save_storage_settings(
                        get_database_path().parent,
                        Path(path_field.value.strip()),
                    )
                    create_configured_database_backups(get_database_path())
                except (OSError, ValueError) as error:
                    error_text.value = str(error)
                    error_text.update()
                    return
                page.pop_dialog()
                self.show_settings()
                self._show_message("Pasta de backup atualizada e primeira cópia criada.")

            page.show_dialog(
                styled_dialog(
                    title="Configurar backup automático",
                    subtitle="Use um caminho existente no próprio computador servidor",
                    icon=ft.Icons.BACKUP_OUTLINED,
                    content=ft.Column(
                        width=600,
                        tight=True,
                        spacing=10,
                        controls=[
                            path_field,
                            dialog_banner(
                                "Digite o caminho do OneDrive ou de outro destino protegido. "
                                "O navegador não pode escolher pastas internas do servidor."
                            ),
                            error_text,
                        ],
                    ),
                    actions=dialog_actions(
                        page=page,
                        primary_label="Salvar e criar cópia",
                        primary_icon=ft.Icons.BACKUP,
                        on_confirm=confirm,
                    ),
                )
            )
            return
        path = await ft.FilePicker().get_directory_path(
            dialog_title="Escolha a pasta das cópias automáticas no OneDrive"
        )
        if not path:
            return
        try:
            save_storage_settings(get_database_path().parent, Path(path))
            create_configured_database_backups(get_database_path())
        except (OSError, ValueError) as error:
            self._show_message(str(error), error=True)
            return
        self.show_settings()
        self._show_message("Pasta de backup atualizada e primeira cópia criada.")

    def _open_data_folder(self) -> None:
        folder = get_database_path().parent
        if _server_mode():
            self._show_message(f"Pasta dos dados no servidor: {folder}")
            return
        if not hasattr(os, "startfile"):
            self._show_message(
                f"A pasta dos dados é: {folder}",
                error=True,
            )
            return
        os.startfile(folder)  # type: ignore[attr-defined]

    def _test_notification(self) -> None:
        try:
            WindowsToastProvider().send(
                "ClimateTest Manager",
                "Notificação de teste enviada com sucesso.",
            )
        except Exception as error:  # pragma: no cover - integração do Windows
            self._show_message(
                f"Não foi possível exibir a notificação: {error}",
                error=True,
            )
            return
        self._show_message("Notificação de teste enviada.")

    def _save_email_settings(
        self,
        settings: EmailSettings,
        new_password: str,
    ) -> str | None:
        if not self._current_user.is_admin:
            return "Somente administradores podem configurar o envio de e-mails."
        current = load_email_settings()
        normalized_new_password = normalize_smtp_password(settings.host, new_password)
        effective_password = normalized_new_password or normalize_smtp_password(
            settings.host,
            current.password,
        )
        if settings.enabled:
            if not 1 <= settings.port <= 65535:
                return "A porta SMTP deve estar entre 1 e 65535."
            if not all(
                (
                    settings.host.strip(),
                    settings.sender.strip(),
                    settings.username.strip(),
                    effective_password,
                )
            ):
                return "Preencha servidor, remetente, usuário e senha SMTP."
            if settings.host.strip().casefold() == "smtp.gmail.com":
                if settings.sender.strip().casefold() != settings.username.strip().casefold():
                    return "No Gmail, o remetente e o usuário SMTP devem ser a mesma conta."
                if len(effective_password) != 16:
                    return (
                        "A senha de app do Gmail deve ter 16 caracteres. "
                        "Os espaços são removidos automaticamente."
                    )
        try:
            save_email_settings(settings, new_password=normalized_new_password)
        except (OSError, ValueError) as error:
            return str(error)
        self.show_settings()
        return None

    def _test_email(self) -> None:
        try:
            settings = load_email_settings()
            automatic_recipients = self._auth_service.list_active_emails(self._current_user)
            test_recipients = list(
                dict.fromkeys(
                    [
                        *automatic_recipients,
                        settings.sender.strip(),
                    ]
                )
            )
            provider = EmailNotificationProvider(
                settings,
                test_recipients,
            )
            receipt = provider.send(
                "Teste de envio",
                "A configuração de e-mail foi validada com sucesso. "
                "Esta mensagem confirma que o servidor SMTP aceitou o teste.",
            )
        except (OSError, ValueError, RuntimeError) as error:
            self._show_message(f"Não foi possível enviar o e-mail: {error}", error=True)
            return
        except Exception as error:  # pragma: no cover - depende do servidor SMTP
            self._show_message(f"Falha no servidor de e-mail: {error}", error=True)
            return
        self._show_email_test_result(receipt)

    def _show_email_test_result(self, receipt: EmailDeliveryReceipt) -> None:
        recipients = "\n".join(f"• {recipient}" for recipient in receipt.recipients)
        page = self._page
        page.show_dialog(
            styled_dialog(
                title="Teste aceito pelo servidor",
                subtitle="O SMTP confirmou o recebimento da mensagem para entrega",
                icon=ft.Icons.MARK_EMAIL_READ_OUTLINED,
                content=ft.Column(
                    width=560,
                    tight=True,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        dialog_banner(
                            "Confira primeiro a caixa do remetente Gmail. Se ela receber e o "
                            "e-mail corporativo não, o bloqueio está no filtro ou na quarentena "
                            "da empresa.",
                            icon=ft.Icons.FACT_CHECK_OUTLINED,
                        ),
                        ft.Text(
                            "Destinatários aceitos:",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(recipients, size=12, selectable=True),
                        ft.Text(
                            f"Identificador da mensagem: {receipt.message_id}",
                            size=10,
                            color=AppColors.TEXT_SECONDARY,
                            selectable=True,
                        ),
                    ],
                ),
                actions=[
                    ft.Button(
                        content="Entendi",
                        icon=ft.Icons.CHECK,
                        bgcolor=AppColors.PRIMARY,
                        color=AppColors.WHITE,
                        on_click=lambda _event: page.pop_dialog(),
                    )
                ],
            )
        )

    async def _select_profile_photo(self, _event: object | None = None) -> None:
        files = await ft.FilePicker().pick_files(
            dialog_title="Escolha uma foto de perfil",
            allow_multiple=False,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["png", "jpg", "jpeg", "webp"],
            with_data=_server_mode(),
        )
        if not files:
            return
        try:
            image_bytes = (
                files[0].bytes
                if files[0].bytes is not None
                else Path(files[0].path or "").read_bytes()
            )
            self._current_user = self._auth_service.set_profile_photo(
                self._current_user,
                image_bytes,
            )
        except (OSError, ValueError) as error:
            self._show_message(str(error), error=True)
            return
        self.show_settings()
        self._show_message("Foto de perfil atualizada.")

    def _remove_profile_photo(self) -> None:
        try:
            self._current_user = self._auth_service.set_profile_photo(
                self._current_user,
                None,
            )
        except ValueError as error:
            self._show_message(str(error), error=True)
            return
        self.show_settings()
        self._show_message("Foto de perfil removida.")

    def _open_github(self) -> None:
        self._page.run_task(
            ft.UrlLauncher().launch_url,
            "https://github.com/jhoncts",
        )

    def _configure_notifications(self, enable: bool) -> None:
        try:
            configure_notification_task(enable=enable)
        except RuntimeError as error:
            self._show_message(str(error), error=True)
            return
        self.show_settings()
        self._show_message(
            "Avisos em segundo plano ativados."
            if enable
            else "Avisos em segundo plano desativados."
        )


class ClimateTestLauncher:
    """Controla configuração inicial, restauração de sessão e entrada no aplicativo."""

    def __init__(
        self,
        page: ft.Page,
        repository: ClimateTestRepository,
        auth_service: AuthenticationService,
        *,
        theme_mode: str,
        local_server_client: bool,
    ) -> None:
        self._page = page
        self._repository = repository
        self._auth_service = auth_service
        self._theme_mode = theme_mode
        self._local_server_client = local_server_client
        self._session_token: str | None = None
        self._switcher = _screen_switcher()
        self._switcher_mounted = False

    def start(self) -> None:
        token = None if _server_mode() else load_remembered_session_token()
        if token:
            user = self._auth_service.restore_session(token)
            if user is not None:
                self._session_token = token
                self._open_application(user)
                return
            with suppress(OSError):
                save_remembered_session_token(None)
        if self._auth_service.requires_initial_setup():
            if self._local_server_client:
                self.show_initial_setup()
            else:
                self._render_entry(build_server_waiting_view())
        else:
            self.show_login()
            recovery_code: str | None = None
            if self._local_server_client:
                with _SERVER_CONTEXT_LOCK:
                    if not self._auth_service.has_administrator_recovery_code():
                        recovery_code = self._auth_service.rotate_administrator_recovery_code()
            if recovery_code is not None:
                self._show_recovery_code(recovery_code)

    def _render_entry(self, content: ft.Control) -> None:
        if not self._switcher_mounted:
            self._page.clean()
            self._page.add(self._switcher)
            self._switcher_mounted = True
        self._switcher.content = content
        self._page.update()

    def show_initial_setup(self) -> None:
        self._render_entry(build_initial_setup_view(self._register_initial_admin))

    def show_login(self) -> None:
        self._session_token = None
        self._render_entry(
            build_login_view(
                self._login,
                on_recover_admin=(
                    self._recover_administrator if self._local_server_client else None
                ),
                allow_remember=not _server_mode(),
            )
        )

    def _register_initial_admin(self, command: UserRegistrationCommand) -> None:
        self._auth_service.register_initial_admin(command)
        recovery_code = self._auth_service.rotate_administrator_recovery_code()
        session = self._auth_service.authenticate(
            command.username,
            command.password,
            remember=False,
        )
        self._session_token = session.token
        self._open_application(session.user)
        self._show_recovery_code(recovery_code)

    def _recover_administrator(
        self,
        recovery_code: str,
        command: UserRegistrationCommand,
    ) -> str:
        if not self._local_server_client:
            raise ValueError("A recuperação só pode ser executada no próprio servidor.")
        _user, next_code = self._auth_service.recover_administrator(
            recovery_code,
            command,
        )
        return next_code

    def _show_recovery_code(self, recovery_code: str) -> None:
        page = self._page
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Guarde o código de recuperação"),
                content=ft.Column(
                    width=540,
                    tight=True,
                    spacing=12,
                    controls=[
                        ft.Text(
                            "Este código permite corrigir a conta administradora somente no "
                            "computador servidor. Ele não será mostrado novamente.",
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
                        ft.Text(
                            "Anote ou imprima e guarde fora do servidor. Não envie o código "
                            "a operadores.",
                            size=12,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
                actions=[
                    ft.Button(
                        content="Já guardei em local seguro",
                        icon=ft.Icons.VERIFIED_USER_OUTLINED,
                        on_click=lambda _event: page.pop_dialog(),
                    )
                ],
            )
        )

    def _login(self, login: str, password: str, remember: bool) -> None:
        remember = remember and not _server_mode()
        session = self._auth_service.authenticate(
            login,
            password,
            remember=remember,
        )
        self._session_token = session.token
        try:
            save_remembered_session_token(session.token if remember else None)
        except OSError:
            if remember:
                self._auth_service.logout(session.token, session.user)
                self._session_token = None
                raise ValueError("Não foi possível salvar a sessão neste computador.") from None
        self._open_application(session.user)

    def _open_application(self, user: UserSummary) -> None:
        ClimateTestApplication(
            self._page,
            self._repository,
            auth_service=self._auth_service,
            current_user=user,
            session_token=self._session_token,
            theme_mode=self._theme_mode,
            on_signed_out=self.show_login,
            host_switcher=self._switcher,
            host_mounted=self._switcher_mounted,
        ).start()


def _configure_page(page: ft.Page, theme_mode: str) -> None:
    """Aplica a moldura da janela tanto ao assistente quanto ao aplicativo."""

    AppColors.apply_mode(theme_mode)
    page.title = "ClimateTest Manager"
    page.theme_mode = ft.ThemeMode.DARK if theme_mode == "dark" else ft.ThemeMode.LIGHT
    page.theme = _application_theme()
    page.padding = 0
    page.spacing = 0
    page.bgcolor = AppColors.PAGE_BACKGROUND
    page.window.width = 1280
    page.window.height = 800
    page.window.min_width = 880
    page.window.min_height = 720
    page.window.icon = "brand/climatetest-logo.png"


def _start_configured_application(page: ft.Page) -> None:
    """Abre o banco somente depois de existir uma decisão de armazenamento."""

    theme_mode = "light" if _server_mode() else load_theme_mode()
    _configure_page(page, theme_mode)

    database_path = get_database_path()
    # Se já houver um banco, a cópia diária é feita antes de qualquer migração.
    with suppress(OSError, ValueError):
        create_configured_database_backups(database_path)
    global _SERVER_AUTH_SERVICE, _SERVER_ENGINE, _SERVER_REPOSITORY
    try:
        if _server_mode():
            with _SERVER_CONTEXT_LOCK:
                if _SERVER_REPOSITORY is None or _SERVER_AUTH_SERVICE is None:
                    engine = initialize_database(database_path)
                    session_factory = create_session_factory(engine)
                    _SERVER_ENGINE = engine
                    _SERVER_REPOSITORY = ClimateTestRepository(session_factory)
                    _SERVER_AUTH_SERVICE = AuthenticationService(UserRepository(session_factory))
                repository = _SERVER_REPOSITORY
                auth_service = _SERVER_AUTH_SERVICE
            engine = _SERVER_ENGINE
        else:
            engine = initialize_database(database_path)
            session_factory = create_session_factory(engine)
            repository = ClimateTestRepository(session_factory)
            auth_service = AuthenticationService(UserRepository(session_factory))
    except Exception as error:  # pragma: no cover - depende do sistema operacional
        page.clean()
        page.add(
            ft.Container(
                padding=32,
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Não foi possível preparar o banco de dados.",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.DANGER,
                        ),
                        ft.Text(str(error), color=AppColors.TEXT_SECONDARY),
                    ]
                ),
            )
        )
        return

    with suppress(OSError, ValueError):
        create_configured_database_backups(database_path)
    if not _server_mode():
        page.on_close = lambda _event: engine.dispose()
    ClimateTestLauncher(
        page,
        repository,
        auth_service,
        theme_mode=theme_mode,
        local_server_client=_local_server_client(page),
    ).start()


def main(page: ft.Page) -> None:
    """Solicita os locais de dados e então inicializa a aplicação desktop."""

    _configure_page(page, "light")
    if not storage_setup_required():
        _start_configured_application(page)
        return
    if _server_mode() and not _local_server_client(page):
        page.clean()
        page.add(build_server_waiting_view())
        return

    def confirm_storage(data_directory: Path, backup_directory: Path | None) -> None:
        save_storage_settings(data_directory, backup_directory)
        _start_configured_application(page)

    page.clean()
    page.add(
        build_storage_setup_view(
            default_data_directory=get_default_data_directory(),
            suggested_backup_directory=suggest_onedrive_backup_directory(),
            on_confirm=confirm_storage,
        )
    )
