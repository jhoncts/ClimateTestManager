"""Sessão persistente e recursos por dispositivo para clientes do servidor central."""

import asyncio
from contextlib import suppress

import flet as ft

from climatetest_manager import app as app_module
from climatetest_manager.client_bridge import (
    TOAST_COMMAND_KEY,
    TOAST_CURSOR_KEY,
    queue_desktop_toast,
)
from climatetest_manager.config import (
    get_database_path,
    get_external_backup_directory,
    load_email_settings,
    load_theme_mode,
    save_theme_mode,
)
from climatetest_manager.services.auth import UserSummary
from climatetest_manager.services.background import notification_task_installed
from climatetest_manager.services.network import get_server_identity
from climatetest_manager.ui.views.managed_settings import build_managed_settings_view

_SESSION_KEY = "climatetest.manager.auth.remembered_session_token.v1"
_PATCHED = False


async def _load_client_token(page: ft.Page) -> str | None:
    """Lê o token persistido no dispositivo que está exibindo a interface."""

    try:
        value = await page.shared_preferences.get(_SESSION_KEY)
    except Exception:
        return None
    return value if isinstance(value, str) and value.strip() else None


async def _save_client_token(page: ft.Page, token: str | None) -> None:
    """Salva ou remove a sessão no armazenamento local do próprio cliente."""

    try:
        if token:
            await page.shared_preferences.set(_SESSION_KEY, token)
        else:
            await page.shared_preferences.remove(_SESSION_KEY)
    except Exception:
        # Persistência é uma conveniência: uma falha local não pode impedir login/logout.
        return


def _notification_marker(notification: object) -> str:
    created_at = getattr(notification, "created_at", None)
    timestamp = created_at.timestamp() if created_at is not None else 0.0
    return (
        f"{timestamp:020.6f}|{getattr(notification, 'source_kind', '')}|"
        f"{int(getattr(notification, 'source_id', 0)):012d}"
    )


_OriginalLauncher = app_module.ClimateTestLauncher
_OriginalApplication = app_module.ClimateTestApplication


class ClientSessionLauncher(_OriginalLauncher):
    """Usa armazenamento do dispositivo, nunca o arquivo de sessão do servidor."""

    def start(self) -> None:
        self._page.run_task(self._start_with_client_session)

    async def _start_with_client_session(self) -> None:
        token = await _load_client_token(self._page)
        if token:
            user = self._auth_service.restore_session(token)
            if user is not None:
                self._session_token = token
                self._open_application(user)
                return
            await _save_client_token(self._page, None)

        if self._auth_service.requires_initial_setup():
            if self._local_server_client:
                self.show_initial_setup()
            else:
                self._render_entry(app_module.build_server_waiting_view())
            return

        self.show_login()
        recovery_code: str | None = None
        if self._local_server_client:
            with app_module._SERVER_CONTEXT_LOCK:
                if not self._auth_service.has_administrator_recovery_code():
                    recovery_code = self._auth_service.rotate_administrator_recovery_code()
        if recovery_code is not None:
            self._show_recovery_code(recovery_code)

    def show_login(self) -> None:
        self._session_token = None
        self._render_entry(
            app_module.build_login_view(
                self._login,
                on_recover_admin=(
                    self._recover_administrator if self._local_server_client else None
                ),
                allow_remember=True,
            )
        )

    def _login(self, login: str, password: str, remember: bool) -> None:
        session = self._auth_service.authenticate(
            login,
            password,
            remember=remember,
        )
        self._session_token = session.token
        self._page.run_task(
            _save_client_token,
            self._page,
            session.token if remember else None,
        )
        self._open_application(session.user)

    def _open_application(self, user: UserSummary) -> None:
        # A preferência visual pertence ao produto central e é reaplicada em todas as sessões.
        theme_mode = load_theme_mode()
        app_module._configure_page(self._page, theme_mode)
        ClientSessionApplication(
            self._page,
            self._repository,
            auth_service=self._auth_service,
            current_user=user,
            session_token=self._session_token,
            theme_mode=theme_mode,
            on_signed_out=self.show_login,
            host_switcher=self._switcher,
            host_mounted=self._switcher_mounted,
        ).start()


class ClientSessionApplication(_OriginalApplication):
    """Adiciona recursos que precisam existir no dispositivo que mostra a sessão remota."""

    def start(self) -> None:
        self._desktop_bridge_active = True
        super().start()
        self._page.run_task(self._poll_desktop_notifications)

    def _change_theme(self, mode: str) -> None:
        """Permite alternar o tema mesmo quando a interface é servida pelo central."""

        self._theme_mode = "dark" if mode == "dark" else "light"
        app_module.AppColors.apply_mode(self._theme_mode)
        self._page.theme_mode = (
            ft.ThemeMode.DARK if self._theme_mode == "dark" else ft.ThemeMode.LIGHT
        )
        self._page.theme = app_module._application_theme()
        self._page.bgcolor = app_module.AppColors.PAGE_BACKGROUND
        try:
            save_theme_mode(self._theme_mode)
        except OSError as error:
            self._show_message(
                f"O tema foi alterado, mas não foi possível salvar a preferência: {error}",
                error=True,
            )
        self.show_settings()

    def show_settings(self) -> None:
        backup_directory = get_external_backup_directory()
        local_server_client = app_module._local_server_client(self._page)
        content = build_managed_settings_view(
            identity=get_server_identity(),
            database_path=get_database_path(),
            backup_directory=backup_directory,
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
                self._configure_backup_directory
                if self._current_user.is_admin and local_server_client
                else None
            ),
            on_report_system_incident=self._report_system_incident,
            on_resolve_system_incident=(
                self._resolve_system_incident if self._current_user.is_admin else None
            ),
            on_refresh=self.show_settings,
            on_rotate_administrator_recovery=(
                self._rotate_administrator_recovery_code
                if self._current_user.is_admin and local_server_client
                else None
            ),
        )
        self._render(content, selected_view="settings")

    def _test_notification(self) -> None:
        async def deliver() -> None:
            sent = await queue_desktop_toast(
                self._page,
                "ClimateTest Manager",
                "Notificação de teste enviada com sucesso para este computador.",
            )
            self._show_message(
                "Notificação enviada para o Windows deste computador."
                if sent
                else "Não foi possível comunicar a notificação ao aplicativo desktop.",
                error=not sent,
            )

        self._page.run_task(deliver)

    async def _wait_command_consumed(self, command_id: str) -> None:
        """Evita sobrescrever um toast se mais de um aviso surgir no mesmo ciclo."""

        for _ in range(20):
            try:
                raw = await self._page.shared_preferences.get(TOAST_COMMAND_KEY)
            except Exception:
                return
            if not isinstance(raw, str) or command_id not in raw:
                return
            await asyncio.sleep(0.25)

    async def _poll_desktop_notifications(self) -> None:
        """Transforma novos avisos do banco central em toasts do Windows da estação."""

        try:
            cursor = await self._page.shared_preferences.get(TOAST_CURSOR_KEY)
        except Exception:
            return
        cursor = cursor if isinstance(cursor, str) else ""

        while self._desktop_bridge_active:
            try:
                notifications = self._repository.list_user_notifications(
                    user_id=self._current_user.id,
                    is_admin=self._current_user.is_admin,
                    limit=40,
                )
                ordered = sorted(notifications, key=_notification_marker)
                if ordered:
                    newest_marker = _notification_marker(ordered[-1])
                    if not cursor:
                        # Primeira conexão não deve disparar dezenas de avisos históricos.
                        cursor = newest_marker
                        await self._page.shared_preferences.set(TOAST_CURSOR_KEY, cursor)
                    else:
                        pending = [
                            notification
                            for notification in ordered
                            if _notification_marker(notification) > cursor
                        ]
                        for notification in pending[-5:]:
                            command_id = (
                                f"{notification.source_kind}-{notification.source_id}-"
                                f"{_notification_marker(notification)}"
                            )
                            sent = await queue_desktop_toast(
                                self._page,
                                notification.title,
                                notification.message.replace("\n", " • "),
                                command_id=command_id,
                            )
                            if sent:
                                await self._wait_command_consumed(command_id)
                        cursor = newest_marker
                        await self._page.shared_preferences.set(TOAST_CURSOR_KEY, cursor)
            except Exception:
                # Um ciclo ruim não deve derrubar a sessão de trabalho.
                pass
            await asyncio.sleep(12)

    def _finish_signed_out(self, message: str | None = None) -> None:
        self._desktop_bridge_active = False
        self._page.run_task(_save_client_token, self._page, None)
        with suppress(Exception):
            self._page.run_task(self._page.shared_preferences.remove, TOAST_CURSOR_KEY)
        super()._finish_signed_out(message)


def enable_client_session_persistence() -> None:
    """Ativa uma vez persistência e recursos locais no modo servidor."""

    global _PATCHED
    if _PATCHED:
        return
    app_module.ClimateTestLauncher = ClientSessionLauncher
    app_module.ClimateTestApplication = ClientSessionApplication
    _PATCHED = True
