"""Aplicação de produção: preferências locais, UI polida e operações multiestação."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from threading import Lock

import flet as ft
from sqlalchemy import Engine

from climatetest_manager import app as legacy
from climatetest_manager.client_bridge import (
    load_local_theme,
    queue_desktop_toast,
    save_local_theme,
    save_offline_snapshot,
)
from climatetest_manager.config import (
    get_database_path,
    get_default_data_directory,
    get_external_backup_directory,
    load_email_settings,
    save_storage_settings,
    storage_setup_required,
    suggest_onedrive_backup_directory,
    test_controls_enabled,
)
from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.production import ProductionClimateTestRepository
from climatetest_manager.repositories.users import UserRepository
from climatetest_manager.services.auth import (
    AuthenticationService,
    UserSummary,
)
from climatetest_manager.services.exports import create_configured_database_backups
from climatetest_manager.services.network import get_server_identity
from climatetest_manager.ui.interaction import apply_interaction_polish
from climatetest_manager.ui.shell import build_production_shell
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.ui.views.agenda import build_agenda_view
from climatetest_manager.ui.views.auth import (
    build_login_view,
    build_server_waiting_view,
    build_storage_setup_view,
)
from climatetest_manager.ui.views.dashboard import build_dashboard
from climatetest_manager.ui.views.history import build_history_view
from climatetest_manager.ui.views.notifications import build_notifications_view
from climatetest_manager.ui.views.onboarding import build_onboarding_view
from climatetest_manager.ui.views.polished_new_test import PolishedNewTestView
from climatetest_manager.ui.views.polished_test_details import build_polished_test_details_view
from climatetest_manager.ui.views.production_settings import build_production_settings_view
from climatetest_manager.ui.views.tests_list import build_tests_list_view
from climatetest_manager.ui.views.users import build_users_view

_REMEMBERED_SESSION_KEY = "climatetest.manager.desktop.remembered-session.v2"
_SERVER_CONTEXT_LOCK = Lock()
_SERVER_ENGINE: Engine | None = None
_SERVER_REPOSITORY: ProductionClimateTestRepository | None = None
_SERVER_AUTH_SERVICE: AuthenticationService | None = None


def _dark_palette(mode: str) -> bool:
    return AppColors.normalize_mode(mode) in {"dark", "graphite", "ocean"}


async def _save_remembered_token(page: ft.Page, token: str | None) -> None:
    if token:
        await page.shared_preferences.set(_REMEMBERED_SESSION_KEY, token)
    else:
        await page.shared_preferences.remove(_REMEMBERED_SESSION_KEY)


async def _load_remembered_token(page: ft.Page) -> str | None:
    value = await page.shared_preferences.get(_REMEMBERED_SESSION_KEY)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _configure_page(page: ft.Page, theme_mode: str) -> None:
    mode = AppColors.normalize_mode(theme_mode)
    AppColors.apply_mode(mode)
    page._climatetest_theme_mode = mode
    page.title = "ClimateTest Manager"
    page.theme_mode = ft.ThemeMode.DARK if _dark_palette(mode) else ft.ThemeMode.LIGHT
    page.theme = legacy._application_theme()
    page.padding = 0
    page.spacing = 0
    page.bgcolor = AppColors.PAGE_BACKGROUND
    page.window.width = 1280
    page.window.height = 800
    page.window.min_width = 880
    page.window.min_height = 720
    page.window.icon = "brand/climatetest-logo.png"


class ProductionClimateTestApplication(legacy.ClimateTestApplication):
    """Finaliza o produto sem duplicar regras de negócio já validadas."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._active_test_id: int | None = None
        self._notification_watch_active = False

    def start(self) -> None:
        self._notification_watch_active = True
        self._page.run_task(self._watch_local_notifications)
        super().start()

    @property
    def _production_repository(self) -> ProductionClimateTestRepository:
        if not isinstance(self._repository, ProductionClimateTestRepository):
            raise RuntimeError("O modo de produção exige ProductionClimateTestRepository.")
        return self._repository

    def _prepare_theme(self) -> None:
        self._theme_mode = AppColors.normalize_mode(self._theme_mode)
        AppColors.apply_mode(self._theme_mode)
        self._page._climatetest_theme_mode = self._theme_mode
        self._page.theme_mode = (
            ft.ThemeMode.DARK if _dark_palette(self._theme_mode) else ft.ThemeMode.LIGHT
        )
        self._page.theme = legacy._application_theme()
        self._page.bgcolor = AppColors.PAGE_BACKGROUND

    def _render(self, content: ft.Control, *, selected_view: str) -> None:
        self._prepare_theme()
        apply_interaction_polish(content)
        super()._render(content, selected_view=selected_view)
        self._page.run_task(self._save_offline_snapshot)

    def _build_current_shell(self) -> ft.Row:
        if self._current_content is None or self._selected_view is None:
            raise RuntimeError("Não há tela selecionada para compor o shell.")
        self._prepare_theme()
        effective_layout = self._layout.with_collapsed_sidebar(self._sidebar_collapsed)
        notification_count = sum(
            not notification.is_read
            for notification in self._production_repository.list_user_notifications(
                user_id=self._current_user.id,
                is_admin=self._current_user.is_admin,
            )
        )
        return build_production_shell(
            self._current_content,
            selected_view=self._selected_view,
            on_dashboard=self.show_dashboard,
            on_tests=self.show_tests,
            on_new_test=self.show_new_test if self._current_user.can_operate else None,
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

    async def _save_offline_snapshot(self) -> None:
        """Atualiza o cache de consulta somente depois de uma leitura válida do servidor."""

        try:
            items = self._service.list_tests()
            summary = self._service.dashboard_summary()
            agenda = self._service.list_agenda_events()
            payload = {
                "schema": 1,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "user": {
                    "name": self._current_user.full_name,
                    "role": self._current_user.role_label,
                },
                "summary": {
                    "in_progress": summary.in_progress,
                    "waiting": summary.waiting,
                    "paused": summary.paused,
                    "overdue": summary.overdue,
                    "due_today": summary.due_today,
                },
                "tests": [
                    {
                        "id": item.id,
                        "client": item.client,
                        "process_number": item.process_number,
                        "product": item.product,
                        "epl": item.epl,
                        "situation": item.situation,
                        "deadline": item.deadline_condition,
                        "temperature": str(item.chamber_temperature_c),
                        "humidity": str(item.chamber_humidity_percent),
                        "duration_hours": item.chamber_duration_hours,
                        "nominal_end_at": (
                            item.nominal_end_at.isoformat(timespec="minutes")
                            if item.nominal_end_at
                            else None
                        ),
                        "maximum_end_at": (
                            item.maximum_end_at.isoformat(timespec="minutes")
                            if item.maximum_end_at
                            else None
                        ),
                    }
                    for item in items[:300]
                ],
                "agenda": [
                    {
                        "test_id": item.test_id,
                        "process_number": item.process_number,
                        "client": item.client,
                        "phase": item.phase,
                        "kind": item.kind,
                        "occurs_at": item.occurs_at.isoformat(timespec="minutes"),
                    }
                    for item in agenda[:300]
                ],
            }
            await save_offline_snapshot(self._page, payload)
        except (OSError, RuntimeError, ValueError):
            # Cache é uma conveniência de disponibilidade; nunca impede a operação online.
            return

    async def _watch_local_notifications(self) -> None:
        """Transforma novos avisos da sessão em toasts no Windows da própria estação."""

        try:
            current = self._production_repository.list_user_notifications(
                user_id=self._current_user.id,
                is_admin=self._current_user.is_admin,
            )
            known = {(item.source_kind, item.source_id) for item in current}
        except (OSError, RuntimeError, ValueError):
            known = set()

        while self._notification_watch_active:
            await asyncio.sleep(5)
            try:
                current = self._production_repository.list_user_notifications(
                    user_id=self._current_user.id,
                    is_admin=self._current_user.is_admin,
                )
            except (OSError, RuntimeError, ValueError):
                continue

            current_keys = {(item.source_kind, item.source_id) for item in current}
            pending = [
                item
                for item in current
                if not item.is_read and (item.source_kind, item.source_id) not in known
            ]
            known = current_keys
            for item in reversed(pending):
                if not self._notification_watch_active:
                    return
                delivered = await queue_desktop_toast(
                    self._page,
                    item.title,
                    item.message,
                    command_id=f"{item.source_kind}-{item.source_id}",
                )
                if item.source_kind == "incident" and self._current_user.is_admin:
                    self._prepare_theme()
                    first_line = (
                        item.message.splitlines()[0] if item.message else "Nova falha registrada"
                    )
                    self._show_message(f"{item.title}: {first_line}")
                if delivered:
                    # O host desktop consome uma chave por vez; evita sobrescrever avisos em rajada.
                    await asyncio.sleep(0.8)

    def _test_notification(self) -> None:
        self._page.run_task(self._send_local_test_notification)

    async def _send_local_test_notification(self) -> None:
        delivered = await queue_desktop_toast(
            self._page,
            "ClimateTest Manager",
            "Notificação de teste enviada com sucesso.",
        )
        if delivered:
            self._show_message("Notificação de teste enviada para este computador.")
            return
        self._show_message(
            "Não foi possível entregar a notificação ao aplicativo desktop deste computador.",
            error=True,
        )

    def show_dashboard(self) -> None:
        self._prepare_theme()
        create_callback = self.show_new_test if self._current_user.can_operate else None
        content = build_dashboard(
            self._service.dashboard_summary(),
            self._service.list_dashboard_tests(),
            self._service.resource_statuses(),
            on_new_test=create_callback,
            on_select=self.show_details,
            on_pause_resource=self._pause_resource,
            on_resume_resource=self._resume_resource,
            read_only=self._current_user.is_viewer,
        )
        self._render(content, selected_view="dashboard")

    def show_new_test(self) -> None:
        if not self._current_user.can_operate:
            self._show_message("Este perfil possui acesso somente para consulta.", error=True)
            return
        if self._selected_view == "new_test" and self._new_test_view is not None:
            return
        self._prepare_theme()
        view = PolishedNewTestView(
            on_cancel=self._confirm_discard_new_test,
            on_save=self._save_test,
            draft=self._new_test_draft,
        )
        self._new_test_view = view
        self._render(view.root, selected_view="new_test")

    def _save_test(self, command) -> None:
        if not self._current_user.can_operate:
            self._show_message("Este perfil possui acesso somente para consulta.", error=True)
            return
        super()._save_test(command)

    def show_edit_test(self, test_id: int) -> None:
        if not self._current_user.can_operate:
            self._show_message("Este perfil possui acesso somente para consulta.", error=True)
            return
        self._prepare_theme()
        view = PolishedNewTestView(
            on_cancel=lambda: self.show_details(test_id),
            on_save=lambda command: self._update_test(test_id, command),
            details=self._service.get_details(test_id),
        )
        self._render(view.root, selected_view="details")

    def show_tests(self) -> None:
        self._prepare_theme()
        content = build_tests_list_view(
            self._service.list_tests(),
            on_select=self.show_details,
            on_new_test=(self.show_new_test if self._current_user.can_operate else None),
            on_export=self._export_csv,
        )
        self._render(content, selected_view="tests")

    def show_details(self, test_id: int) -> None:
        self._prepare_theme()
        self._active_test_id = test_id
        details = self._service.get_details(test_id)
        content = build_polished_test_details_view(
            details,
            on_back=self.show_tests,
            read_only=self._current_user.is_viewer,
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
            on_admin_delete=(
                lambda reason: (
                    self._delete_test_as_admin(test_id, reason)
                    if self._current_user.is_admin
                    else None
                )
            ),
            on_change_timestamp=lambda timestamp, value, reason: self._perform(
                test_id,
                lambda: self._service.change_operational_timestamp(
                    test_id, timestamp, value, reason
                ),
                "Horário operacional corrigido e alteração registrada.",
            ),
            on_advance_for_testing=(
                lambda: (
                    self._perform(
                        test_id,
                        lambda: self._service.advance_for_testing(test_id),
                        "Etapa avançada somente para validação.",
                    )
                    if test_controls_enabled()
                    else None
                )
            ),
        )
        self._render(content, selected_view="details")

    def _delete_test_as_admin(self, test_id: int, reason: str) -> None:
        if not self._current_user.is_admin:
            self._show_message("Somente administradores podem excluir ensaios.", error=True)
            return
        try:
            self._production_repository.delete_test_as_administrator(
                test_id,
                actor_user_id=self._current_user.id,
                actor_label=self._current_user.actor_label,
                reason=reason,
            )
        except (LookupError, ValueError) as error:
            self._show_message(str(error), error=True)
            return
        self._active_test_id = None
        self.show_tests()
        self._show_message(
            f"Ensaio #{test_id} removido da operação. "
            "A exclusão permaneceu registrada na auditoria."
        )

    def show_history(self) -> None:
        self._prepare_theme()
        self._render(
            build_history_view(self._service.list_history(), on_select=self.show_details),
            selected_view="history",
        )

    def show_notifications(self) -> None:
        self._prepare_theme()
        notifications = self._production_repository.list_user_notifications(
            user_id=self._current_user.id,
            is_admin=self._current_user.is_admin,
        )
        content = build_notifications_view(
            notifications,
            is_admin=self._current_user.is_admin,
            on_mark_read=self._mark_notification_read,
            on_mark_all_read=lambda: self._mark_all_notifications_read(notifications),
            on_mark_many_read=self._mark_many_notifications_read,
            on_dismiss=self._dismiss_notification,
            on_dismiss_many=self._dismiss_many_notifications,
        )
        self._render(content, selected_view="notifications")

    def _mark_many_notifications_read(self, sources: list[tuple[str, int]]) -> None:
        for source_kind, source_id in dict.fromkeys(sources):
            self._production_repository.mark_user_notification_read(
                user_id=self._current_user.id,
                source_kind=source_kind,
                source_id=source_id,
            )
        self.show_notifications()

    def _dismiss_notification(self, source_kind: str, source_id: int) -> None:
        self._production_repository.dismiss_user_notification(
            user_id=self._current_user.id,
            source_kind=source_kind,
            source_id=source_id,
        )
        self.show_notifications()

    def _dismiss_many_notifications(self, sources: list[tuple[str, int]]) -> None:
        self._production_repository.dismiss_user_notifications(
            user_id=self._current_user.id,
            sources=sources,
        )
        self.show_notifications()

    def show_agenda(self) -> None:
        self._prepare_theme()
        self._render(
            build_agenda_view(self._service.list_agenda_events(), on_select=self.show_details),
            selected_view="agenda",
        )

    def show_settings(self) -> None:
        self._prepare_theme()
        content = build_production_settings_view(
            identity=get_server_identity(),
            database_path=get_database_path(),
            backup_directory=get_external_backup_directory(),
            notifications_enabled=legacy.notification_task_installed(),
            notification_status=self._service.notification_status(),
            email_settings=load_email_settings(),
            email_recipients=(
                self._auth_service.list_active_emails(self._current_user)
                if self._current_user.is_admin
                else []
            ),
            system_incidents=(
                self._production_repository.list_system_incidents()
                if self._current_user.is_admin
                else []
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
            on_report_system_incident=(
                self._report_system_incident if self._current_user.can_operate else None
            ),
            on_resolve_system_incident=(
                self._resolve_system_incident if self._current_user.is_admin else None
            ),
            on_refresh=self.show_settings,
            on_rotate_administrator_recovery=(
                self._rotate_administrator_recovery_code
                if self._current_user.is_admin and legacy._local_server_client(self._page)
                else None
            ),
        )
        self._render(content, selected_view="settings")

    def _change_theme(self, mode: str) -> None:
        self._theme_mode = AppColors.normalize_mode(mode)
        self._prepare_theme()
        self._page.run_task(save_local_theme, self._page, self._theme_mode)
        selected = self._selected_view or "settings"
        if selected == "dashboard":
            self.show_dashboard()
        elif selected == "tests":
            self.show_tests()
        elif selected == "details" and self._active_test_id is not None:
            self.show_details(self._active_test_id)
        elif selected == "agenda":
            self.show_agenda()
        elif selected == "history":
            self.show_history()
        elif selected == "notifications":
            self.show_notifications()
        elif selected == "users":
            self.show_users()
        elif selected == "help":
            self.show_help()
        elif selected == "new_test":
            # O rascunho é preservado antes da reconstrução do formulário.
            if self._new_test_view is not None:
                self._new_test_draft = self._new_test_view.snapshot_draft()
            self._new_test_view = None
            self.show_new_test()
        else:
            self.show_settings()

    def show_help(self, *, first_access: bool = False) -> None:
        self._prepare_theme()
        content = build_onboarding_view(
            user_name=self._current_user.first_name,
            on_complete=(self._complete_onboarding if first_access else self.show_dashboard),
            first_access=first_access,
        )
        self._render(content, selected_view="help")

    def show_users(self) -> None:
        if not self._current_user.is_admin:
            self._show_message("Somente administradores podem gerenciar usuários.", error=True)
            return
        self._prepare_theme()
        content = build_users_view(
            self._auth_service.list_users(self._current_user),
            current_user=self._current_user,
            on_create=self._create_user,
            on_update=self._update_user,
            on_reset_password=self._reset_user_password,
        )
        self._render(content, selected_view="users")

    def _finish_signed_out(self, message: str | None = None) -> None:
        self._notification_watch_active = False
        self._session_token = None
        self._page.run_task(_save_remembered_token, self._page, None)
        self._page.on_resize = None
        self._on_signed_out()
        if message:
            self._show_message(message)


class ProductionClimateTestLauncher(legacy.ClimateTestLauncher):
    """Restaura sessão e tema a partir do dispositivo, nunca do banco compartilhado."""

    def __init__(self, *args, remembered_token: str | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._remembered_token = remembered_token

    def start(self) -> None:
        if self._remembered_token:
            user = self._auth_service.restore_session(self._remembered_token)
            if user is not None:
                self._session_token = self._remembered_token
                self._open_application(user)
                return
            self._page.run_task(_save_remembered_token, self._page, None)
        if self._auth_service.requires_initial_setup():
            if self._local_server_client:
                self.show_initial_setup()
            else:
                self._render_entry(build_server_waiting_view())
        else:
            self.show_login()
            recovery_code: str | None = None
            if self._local_server_client:
                with legacy._SERVER_CONTEXT_LOCK:
                    if not self._auth_service.has_administrator_recovery_code():
                        recovery_code = self._auth_service.rotate_administrator_recovery_code()
            if recovery_code is not None:
                self._show_recovery_code(recovery_code)

    def show_login(self) -> None:
        self._session_token = None
        self._render_entry(
            build_login_view(
                self._login,
                on_recover_admin=(
                    self._recover_administrator if self._local_server_client else None
                ),
                allow_remember=True,
            )
        )

    def _login(self, login: str, password: str, remember: bool) -> None:
        session = self._auth_service.authenticate(login, password, remember=remember)
        self._session_token = session.token
        self._page.run_task(
            _save_remembered_token,
            self._page,
            session.token if remember else None,
        )
        self._open_application(session.user)

    def _open_application(self, user: UserSummary) -> None:
        ProductionClimateTestApplication(
            self._page,
            self._repository,
            auth_service=self._auth_service,
            current_user=user,
            session_token=self._session_token,
            theme_mode=self._theme_mode,
            on_signed_out=self._signed_out,
            host_switcher=self._switcher,
            host_mounted=self._switcher_mounted,
        ).start()

    def _signed_out(self) -> None:
        self._session_token = None
        self._remembered_token = None
        self._page.run_task(_save_remembered_token, self._page, None)
        self.show_login()


async def _start_configured_application(page: ft.Page, theme_mode: str) -> None:
    _configure_page(page, theme_mode)
    database_path = get_database_path()
    with suppress(OSError, ValueError):
        create_configured_database_backups(database_path)

    global _SERVER_AUTH_SERVICE, _SERVER_ENGINE, _SERVER_REPOSITORY
    try:
        if legacy._server_mode():
            with _SERVER_CONTEXT_LOCK:
                if _SERVER_REPOSITORY is None or _SERVER_AUTH_SERVICE is None:
                    engine = initialize_database(database_path)
                    session_factory = create_session_factory(engine)
                    _SERVER_ENGINE = engine
                    _SERVER_REPOSITORY = ProductionClimateTestRepository(session_factory)
                    _SERVER_AUTH_SERVICE = AuthenticationService(UserRepository(session_factory))
                repository = _SERVER_REPOSITORY
                auth_service = _SERVER_AUTH_SERVICE
            engine = _SERVER_ENGINE
        else:
            engine = initialize_database(database_path)
            session_factory = create_session_factory(engine)
            repository = ProductionClimateTestRepository(session_factory)
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

    if not legacy._server_mode() and engine is not None:
        page.on_close = lambda _event: engine.dispose()
    remembered_token = await _load_remembered_token(page)
    ProductionClimateTestLauncher(
        page,
        repository,
        auth_service,
        theme_mode=theme_mode,
        local_server_client=legacy._local_server_client(page),
        remembered_token=remembered_token,
    ).start()


async def main(page: ft.Page) -> None:
    """Entrada de produção hospedada pelo servidor central."""

    theme_mode = AppColors.normalize_mode(await load_local_theme(page, "light"))
    _configure_page(page, theme_mode)
    if not storage_setup_required():
        await _start_configured_application(page, theme_mode)
        return
    if legacy._server_mode() and not legacy._local_server_client(page):
        page.clean()
        page.add(build_server_waiting_view())
        return

    def confirm_storage(data_directory: Path, backup_directory: Path | None) -> None:
        save_storage_settings(data_directory, backup_directory)
        page.run_task(_start_configured_application, page, theme_mode)

    page.clean()
    page.add(
        build_storage_setup_view(
            default_data_directory=get_default_data_directory(),
            suggested_backup_directory=suggest_onedrive_backup_directory(),
            on_confirm=confirm_storage,
        )
    )
