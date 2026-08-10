"""Sessão persistente por dispositivo para clientes conectados ao servidor central."""

from contextlib import suppress

from climatetest_manager import app as app_module
from climatetest_manager.services.auth import UserSummary

_SESSION_KEY = "climatetest.manager.auth.remembered_session_token.v1"
_PATCHED = False


async def _load_client_token(page: object) -> str | None:
    """Lê o token persistido no dispositivo que está exibindo a interface."""

    try:
        preferences = getattr(page, "shared_preferences")
        value = await preferences.get(_SESSION_KEY)
    except Exception:
        return None
    return value if isinstance(value, str) and value.strip() else None


async def _save_client_token(page: object, token: str | None) -> None:
    """Salva ou remove a sessão no armazenamento local do próprio cliente."""

    try:
        preferences = getattr(page, "shared_preferences")
        if token:
            await preferences.set(_SESSION_KEY, token)
        else:
            await preferences.remove(_SESSION_KEY)
    except Exception:
        # Persistência é uma conveniência: uma falha local não pode impedir login/logout.
        return


_OriginalLauncher = app_module.ClimateTestLauncher
_OriginalApplication = app_module.ClimateTestApplication


class ClientSessionLauncher(_OriginalLauncher):
    """Usa armazenamento do dispositivo, nunca o arquivo de preferências do servidor."""

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
        # Mantido explícito para que o aplicativo aberto use a subclasse abaixo.
        ClientSessionApplication(
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


class ClientSessionApplication(_OriginalApplication):
    """Remove também a sessão persistente do dispositivo ao sair da conta."""

    def _finish_signed_out(self, message: str | None = None) -> None:
        self._page.run_task(_save_client_token, self._page, None)
        with suppress(Exception):
            super()._finish_signed_out(message)


def enable_client_session_persistence() -> None:
    """Ativa uma vez a persistência segura por dispositivo no modo servidor."""

    global _PATCHED
    if _PATCHED:
        return
    app_module.ClimateTestLauncher = ClientSessionLauncher
    app_module.ClimateTestApplication = ClientSessionApplication
    _PATCHED = True
