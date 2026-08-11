"""Cliente desktop nativo que conecta ao servidor central do ClimateTest Manager."""

import argparse  # noqa: I001
import asyncio
import os
import sys
import threading
import urllib.error
import urllib.request
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import flet as ft

from climatetest_manager.client_bridge import (
    DesktopToastCommand,
    TOAST_COMMAND_KEY,
    load_offline_snapshot,
)
from climatetest_manager.services.notifications import WindowsToastProvider
from climatetest_manager.services.updates import (
    automatic_update_checks_enabled,
    check_for_update,
    download_verified_update,
    launch_installer_elevated,
)
from climatetest_manager.single_instance import SingleInstanceCoordinator
from climatetest_manager.ui.offline import build_offline_view

VERSION = "0.7.0"
DEFAULT_PORT = 8550
SERVER_CONFIG_FILENAME = "server.url"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--url", default="")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--ready-file", default="", help=argparse.SUPPRESS)
    parser.add_argument("--no-tray", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-single-instance", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def _program_data_directory() -> Path:
    program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    return Path(program_data) / "ClimateTestManager"


def _server_config_path() -> Path:
    return _program_data_directory() / SERVER_CONFIG_FILENAME


def _read_server_config() -> str:
    try:
        return _server_config_path().read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _normalize_server_url(value: str) -> str:
    """Aceita nome, IP ou URL e devolve o endereço HTTP usado pelo cliente."""

    raw = value.strip().rstrip("/")
    if not raw:
        raw = f"http://localhost:{DEFAULT_PORT}"
    elif "://" not in raw:
        raw = f"http://{raw}"

    parsed = urlsplit(raw)
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Endereço do servidor inválido.")
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("Porta do servidor inválida.") from error

    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = f"{host}:{port or DEFAULT_PORT}"
    return urlunsplit((parsed.scheme.casefold(), netloc, "", "", ""))


def _resolve_server_url(explicit_url: str = "") -> str:
    configured = (
        explicit_url.strip()
        or os.environ.get("CLIMATETEST_SERVER_URL", "").strip()
        or _read_server_config()
        or f"http://localhost:{DEFAULT_PORT}"
    )
    return _normalize_server_url(configured)


def _server_available(server_url: str, *, timeout: float = 1.5) -> bool:
    try:
        request = urllib.request.Request(
            server_url,
            method="GET",
            headers={"User-Agent": f"ClimateTestManager/{VERSION}"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (OSError, urllib.error.URLError, ValueError):
        return False


def _configure_page(page: ft.Page) -> None:
    page.title = "ClimateTest Manager"
    page.padding = 0
    page.spacing = 0
    page.bgcolor = "#EDF3F8"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 1280
    page.window.height = 800
    page.window.min_width = 900
    page.window.min_height = 700
    page.window.icon = "brand/climatetest.ico"


def _splash_card(status: ft.Text, retry: ft.Button) -> ft.Container:
    return ft.Container(
        expand=True,
        bgcolor="#EDF3F8",
        alignment=ft.Alignment.CENTER,
        content=ft.Container(
            width=430,
            padding=36,
            border_radius=24,
            bgcolor="#FFFFFF",
            shadow=ft.BoxShadow(
                blur_radius=32,
                spread_radius=1,
                color="#220F172A",
                offset=ft.Offset(0, 12),
            ),
            content=ft.Column(
                tight=True,
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=92,
                        height=92,
                        padding=6,
                        border_radius=22,
                        bgcolor="#FFFFFF",
                        content=ft.Image(
                            src="brand/climatetest-logo.png",
                            fit=ft.BoxFit.CONTAIN,
                            filter_quality=ft.FilterQuality.HIGH,
                            anti_alias=True,
                            semantics_label="Logo do ClimateTest Manager",
                        ),
                    ),
                    ft.Text(
                        "ClimateTest Manager",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color="#102A43",
                    ),
                    ft.Text(
                        "Gestão de ensaios laboratoriais",
                        size=13,
                        color="#66788A",
                    ),
                    ft.Container(height=6),
                    ft.ProgressRing(
                        width=28,
                        height=28,
                        stroke_width=3,
                        color="#087E8B",
                    ),
                    status,
                    retry,
                    ft.Text(
                        f"Cliente desktop v{VERSION}",
                        size=10,
                        color="#8292A3",
                    ),
                ],
            ),
        ),
    )


def _write_ready_marker(path: Path, server_url: str) -> None:
    """Marca a inicialização real da interface para o smoke test do executável Windows."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        f"ClimateTest Manager\n{server_url}\n",
        encoding="utf-8",
    )
    temporary.replace(path)


class _TrayController:
    """Bandeja nativa do Windows sem misturar o loop do Flet com o do shell."""

    def __init__(self, page: ft.Page, assets_directory: Path, *, disabled: bool = False) -> None:
        self._page = page
        self._assets_directory = assets_directory
        self._disabled = disabled
        self._icon: object | None = None
        self._thread: threading.Thread | None = None
        self._exiting = False
        self._hidden_notice_sent = False

    @property
    def active(self) -> bool:
        return self._icon is not None and not self._exiting

    def start(self) -> bool:
        if (
            self._disabled
            or sys.platform != "win32"
            or os.environ.get("GITHUB_ACTIONS", "").casefold() == "true"
        ):
            return False
        try:
            import pystray
            from PIL import Image

            logo = self._assets_directory / "brand" / "climatetest-logo.png"
            with Image.open(logo) as opened:
                icon_image = opened.convert("RGBA").copy()
            menu = pystray.Menu(
                pystray.MenuItem(
                    "Abrir ClimateTest Manager",
                    self._open_from_tray,
                    default=True,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Sair", self._exit_from_tray),
            )
            self._icon = pystray.Icon(
                "ClimateTestManager",
                icon=icon_image,
                title="ClimateTest Manager",
                menu=menu,
            )
            self._thread = threading.Thread(
                target=self._icon.run,
                name="ClimateTestManagerTray",
                daemon=True,
            )
            self._thread.start()
            return True
        except Exception:
            self._icon = None
            return False

    def _open_from_tray(self, _icon: object, _item: object) -> None:
        self._page.run_task(self.show_window)

    def _exit_from_tray(self, _icon: object, _item: object) -> None:
        self._page.run_task(self.exit_application)

    async def show_window(self) -> None:
        self._page.window.skip_task_bar = False
        self._page.window.visible = True
        self._page.update()
        await self._page.window.to_front()

    async def hide_window(self) -> None:
        self._page.window.visible = False
        self._page.window.skip_task_bar = True
        self._page.update()
        if not self._hidden_notice_sent:
            self._hidden_notice_sent = True
            self.notify(
                "ClimateTest Manager",
                "O aplicativo continua ativo em segundo plano. "
                "Use o ícone ao lado do relógio para abrir novamente.",
            )

    async def exit_application(self) -> None:
        self._exiting = True
        icon = self._icon
        self._icon = None
        if icon is not None:
            with suppress(Exception):
                icon.stop()
        self._page.window.prevent_close = False
        await self._page.window.destroy()

    def notify(self, title: str, message: str) -> None:
        icon = self._icon
        if icon is not None:
            try:
                icon.notify(message, title)
                return
            except Exception:
                pass
        try:
            WindowsToastProvider().send(title, message)
        except Exception:
            return


async def _watch_desktop_commands(page: ft.Page, tray: _TrayController) -> None:
    """Entrega localmente os toasts solicitados pela sessão remota."""

    last_id = ""
    while True:
        try:
            raw = await page.shared_preferences.get(TOAST_COMMAND_KEY)
            if isinstance(raw, str) and raw.strip():
                command = DesktopToastCommand.from_json(raw)
                if command.command_id != last_id:
                    tray.notify(command.title, command.message)
                    last_id = command.command_id
                await page.shared_preferences.remove(TOAST_COMMAND_KEY)
        except Exception:
            pass
        await asyncio.sleep(0.6)


async def _watch_activation_requests(
    page: ft.Page,
    tray: _TrayController,
    coordinator: SingleInstanceCoordinator | None,
) -> None:
    """Traz a janela existente para frente quando o atalho é clicado novamente."""

    if coordinator is None:
        return
    while True:
        if coordinator.consume_activation_request():
            if tray.active:
                await tray.show_window()
            else:
                page.window.visible = True
                page.window.skip_task_bar = False
                page.update()
                with suppress(Exception):
                    await page.window.to_front()
        await asyncio.sleep(0.2)


async def _offer_available_update(page: ft.Page, tray: _TrayController) -> None:
    """Consulta sem bloquear a UI e oferece apenas instaladores com SHA-256 válido."""

    if not automatic_update_checks_enabled():
        return
    update = await asyncio.to_thread(check_for_update, VERSION)
    if update is None:
        return

    progress = ft.ProgressRing(width=20, height=20, stroke_width=2, visible=False)
    status = ft.Text("", size=11, color="#66788A")
    install_button: ft.Button

    async def download_and_install() -> None:
        install_button.disabled = True
        progress.visible = True
        status.value = "Baixando e verificando a atualização..."
        status.color = "#66788A"
        page.update()
        try:
            installer = await asyncio.to_thread(download_verified_update, update)
            status.value = "Integridade confirmada. Solicitando permissão do Windows..."
            page.update()
            launched = await asyncio.to_thread(launch_installer_elevated, installer)
            if not launched:
                raise OSError("O Windows não iniciou o instalador com permissão administrativa.")
        except (OSError, ValueError) as error:
            progress.visible = False
            install_button.disabled = False
            status.value = f"Não foi possível atualizar: {error}"
            status.color = "#B42318"
            page.update()
            return

        with suppress(Exception):
            page.pop_dialog()
        if tray.active:
            await tray.exit_application()
        else:
            await page.window.destroy()

    def start_update(_event: object | None = None) -> None:
        page.run_task(download_and_install)

    notes = update.release_notes.strip()
    notes_control: list[ft.Control] = []
    if notes:
        notes_control.append(
            ft.Container(
                border_radius=10,
                bgcolor="#F4F7FA",
                padding=10,
                content=ft.Text(
                    notes[:1200],
                    size=10,
                    color="#536579",
                    max_lines=8,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            )
        )

    install_button = ft.Button(
        content="Baixar e instalar",
        icon=ft.Icons.SYSTEM_UPDATE_ALT,
        bgcolor="#087E8B",
        color="#FFFFFF",
        on_click=start_update,
    )
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Nova atualização disponível", weight=ft.FontWeight.BOLD),
        content=ft.Column(
            tight=True,
            spacing=12,
            controls=[
                ft.Text(
                    f"ClimateTest Manager v{update.version} está disponível. "
                    f"Versão instalada: v{VERSION}.",
                    size=12,
                ),
                *notes_control,
                ft.Row(spacing=10, controls=[progress, status]),
                ft.Text(
                    "O instalador é baixado do GitHub e só é executado depois da "
                    "verificação do SHA-256 publicado.",
                    size=10,
                    color="#66788A",
                ),
            ],
        ),
        actions=[
            ft.TextButton(content="Agora não", on_click=lambda _event: page.pop_dialog()),
            install_button,
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.open(dialog)


def _remote_app(server_url: str, on_error) -> ft.FletApp:
    """Cria uma sessão nova; recriá-la evita a tela branca após perda prolongada da LAN."""

    return ft.FletApp(
        url=server_url,
        expand=True,
        reconnect_interval_ms=1000,
        reconnect_timeout_ms=7000,
        on_error=on_error,
        app_error_message="Reconectando ao servidor central... {message}",
        boot_screen_options={
            "theme_mode": "light",
            "bgcolor_light": "#EDF3F8",
            "bgcolor_dark": "#102A43",
            "spinner_size": 0,
            "startup_message": "",
        },
    )


async def desktop_main(
    page: ft.Page,
    server_url: str,
    *,
    ready_file: Path | None = None,
    no_tray: bool = False,
    coordinator: SingleInstanceCoordinator | None = None,
) -> None:
    """Supervisiona a sessão remota e nunca deixa uma estação presa em tela branca."""

    _configure_page(page)
    server_url = server_url.rstrip("/")
    assets_directory = Path(__file__).resolve().parent / "assets"
    tray = _TrayController(page, assets_directory, disabled=no_tray)
    tray_active = tray.start()
    if tray_active:
        page.window.prevent_close = True

        def on_window_event(event: ft.WindowEvent) -> None:
            if event.type == ft.WindowEventType.CLOSE and not tray._exiting:
                page.run_task(tray.hide_window)

        page.window.on_event = on_window_event
        page.run_task(_watch_desktop_commands, page, tray)
    page.run_task(_watch_activation_requests, page, tray, coordinator)

    status = ft.Text(
        "Conectando ao computador central...",
        size=12,
        color="#66788A",
        text_align=ft.TextAlign.CENTER,
    )
    retry = ft.Button(
        content="Tentar novamente",
        icon=ft.Icons.REFRESH,
        visible=False,
    )
    splash = _splash_card(status, retry)
    splash.opacity = 1
    splash.animate_opacity = 220
    embedded_host = ft.Container(expand=True, opacity=0, animate_opacity=180)
    offline_host = ft.Container(expand=True, visible=False)
    root = ft.Stack(expand=True, controls=[embedded_host, offline_host, splash])
    page.add(root)
    page.update()

    state = {"online": False, "reconnecting": False, "update_checked": False, "failures": 0}

    async def show_offline() -> None:
        snapshot = await load_offline_snapshot(page)
        offline_host.content = build_offline_view(
            snapshot,
            server_url=server_url,
            on_retry=lambda _event: page.run_task(reconnect),
        )
        state["online"] = False
        state["reconnecting"] = False
        embedded_host.opacity = 0
        offline_host.visible = True
        splash.visible = False
        page.update()

    async def handle_remote_error(_event: object | None = None) -> None:
        # A sessão embutida pode emitir erro antes do watchdog perceber a queda.
        await asyncio.sleep(0.15)
        if not await asyncio.to_thread(_server_available, server_url):
            await show_offline()
        else:
            await reconnect(force=True)

    async def reconnect(_event: object | None = None, *, force: bool = False) -> None:
        if state["reconnecting"]:
            return
        state["reconnecting"] = True
        splash.visible = True
        splash.opacity = 1
        retry.visible = False
        offline_host.visible = False
        status.value = "Reconectando ao computador central..."
        status.color = "#66788A"
        page.update()

        ready = force or await asyncio.to_thread(_server_available, server_url)
        if not ready:
            state["reconnecting"] = False
            await show_offline()
            return

        status.value = "Servidor encontrado. Restaurando a interface..."
        status.color = "#087E8B"
        embedded_host.content = _remote_app(server_url, handle_remote_error)
        embedded_host.opacity = 1
        state["online"] = True
        state["failures"] = 0
        page.update()
        await asyncio.sleep(0.75)
        splash.opacity = 0
        page.update()
        await asyncio.sleep(0.2)
        splash.visible = False
        state["reconnecting"] = False
        page.update()
        if ready_file is not None:
            await asyncio.to_thread(_write_ready_marker, ready_file, server_url)
        if not state["update_checked"]:
            state["update_checked"] = True
            page.run_task(_offer_available_update, page, tray)

    retry.on_click = lambda _event: page.run_task(reconnect)

    async def initial_connection() -> None:
        for attempt in range(1, 11):
            if await asyncio.to_thread(_server_available, server_url):
                await reconnect(force=True)
                return
            status.value = f"Aguardando o servidor central... tentativa {attempt}/10"
            page.update()
            await asyncio.sleep(0.6)
        await show_offline()

    async def connection_watchdog() -> None:
        """Detecta perda e retorno da LAN sem depender do estado interno do WebView/FletApp."""

        while True:
            await asyncio.sleep(2.5)
            available = await asyncio.to_thread(_server_available, server_url)
            if available:
                state["failures"] = 0
                if not state["online"] and not state["reconnecting"]:
                    await reconnect(force=True)
                continue
            if not state["online"]:
                continue
            state["failures"] = int(state["failures"]) + 1
            if state["failures"] >= 2:
                await show_offline()

    page.run_task(initial_connection)
    page.run_task(connection_watchdog)


def _build_page_handler(
    server_url: str,
    *,
    ready_file: Path | None = None,
    no_tray: bool = False,
    coordinator: SingleInstanceCoordinator | None = None,
):
    """Devolve um handler realmente assíncrono para que o Flet aguarde a montagem da página."""

    async def page_handler(page: ft.Page) -> None:
        await desktop_main(
            page,
            server_url,
            ready_file=ready_file,
            no_tray=no_tray,
            coordinator=coordinator,
        )

    return page_handler


def main() -> None:
    arguments = _arguments()
    try:
        server_url = _resolve_server_url(arguments.url)
    except ValueError:
        raise SystemExit(21) from None

    if arguments.check_only:
        raise SystemExit(0 if _server_available(server_url, timeout=3) else 20)

    coordinator: SingleInstanceCoordinator | None = None
    if not arguments.no_single_instance:
        coordinator = SingleInstanceCoordinator()
        if not coordinator.acquire_or_signal():
            return

    ready_file = Path(arguments.ready_file).expanduser() if arguments.ready_file.strip() else None
    assets_directory = Path(__file__).resolve().parent / "assets"
    try:
        ft.run(
            _build_page_handler(
                server_url,
                ready_file=ready_file,
                no_tray=arguments.no_tray,
                coordinator=coordinator,
            ),
            assets_dir=str(assets_directory),
        )
    finally:
        if coordinator is not None:
            coordinator.close()


if __name__ == "__main__":
    main()
