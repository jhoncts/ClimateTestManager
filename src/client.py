"""Cliente desktop nativo que conecta ao servidor central do ClimateTest Manager."""

import argparse
import asyncio
import os
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import flet as ft

from climatetest_manager.client_bridge import DesktopToastCommand, TOAST_COMMAND_KEY
from climatetest_manager.services.notifications import WindowsToastProvider

VERSION = "0.7.0"
DEFAULT_PORT = 8550
SERVER_CONFIG_FILENAME = "server.url"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--url", default="")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--ready-file", default="", help=argparse.SUPPRESS)
    parser.add_argument("--no-tray", action="store_true", help=argparse.SUPPRESS)
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
                "O aplicativo continua ativo em segundo plano. Use o ícone ao lado do relógio para abrir novamente.",
            )

    async def exit_application(self) -> None:
        self._exiting = True
        icon = self._icon
        self._icon = None
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass
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


async def desktop_main(
    page: ft.Page,
    server_url: str,
    *,
    ready_file: Path | None = None,
    no_tray: bool = False,
) -> None:
    """Mantém o servidor invisível e mostra somente uma janela própria do aplicativo."""

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

    status = ft.Text(
        "Conectando ao computador central...",
        size=12,
        color="#66788A",
        text_align=ft.TextAlign.CENTER,
    )

    async def retry_connection(_event: object | None = None) -> None:
        retry.visible = False
        status.value = "Conectando ao computador central..."
        status.color = "#66788A"
        page.update()
        await reveal_when_ready()

    retry = ft.Button(
        content="Tentar novamente",
        icon=ft.Icons.REFRESH,
        visible=False,
        on_click=retry_connection,
    )
    splash = _splash_card(status, retry)
    splash.opacity = 1
    splash.animate_opacity = 280

    embedded_app: ft.Container

    def embedded_error(event: object) -> None:
        message = str(getattr(event, "data", "") or "falha de comunicação com a interface")
        embedded_app.opacity = 0
        splash.visible = True
        splash.opacity = 1
        status.value = (
            "O servidor respondeu, mas a interface não conseguiu ser carregada. "
            f"Código CTM-UI-002. Detalhes: {message}"
        )
        status.color = "#B42318"
        retry.visible = True
        page.update()

    embedded_app = ft.Container(
        expand=True,
        opacity=0,
        animate_opacity=280,
        content=ft.FletApp(
            url=server_url,
            expand=True,
            reconnect_interval_ms=1500,
            reconnect_timeout_ms=30000,
            on_error=embedded_error,
            app_error_message=(
                "Não foi possível manter a conexão com o servidor central. "
                "Aguarde alguns segundos ou reinicie o ClimateTest Manager. "
                "Detalhes: {message}"
            ),
            boot_screen_options={
                "theme_mode": "light",
                "bgcolor_light": "#EDF3F8",
                "bgcolor_dark": "#102A43",
                "spinner_size": 0,
                "startup_message": "",
            },
        ),
    )
    root = ft.Stack(expand=True, controls=[embedded_app, splash])
    page.add(root)
    page.update()

    async def reveal_when_ready() -> None:
        ready = False
        for attempt in range(1, 16):
            ready = await asyncio.to_thread(_server_available, server_url)
            if ready:
                break
            status.value = f"Aguardando o servidor central... tentativa {attempt}/15"
            page.update()
            await asyncio.sleep(0.7)

        if not ready:
            status.value = (
                "Servidor indisponível. Confirme se o computador central está ligado e conectado "
                f"à rede. Servidor configurado: {server_url}. Código CTM-CLI-001."
            )
            status.color = "#B42318"
            retry.visible = True
            page.update()
            return

        status.value = "Servidor encontrado. Abrindo o ClimateTest Manager..."
        status.color = "#087E8B"
        page.update()
        await asyncio.sleep(0.9)
        embedded_app.opacity = 1
        splash.opacity = 0
        page.update()
        await asyncio.sleep(0.35)
        splash.visible = False
        page.update()
        if ready_file is not None:
            await asyncio.to_thread(_write_ready_marker, ready_file, server_url)

    page.run_task(reveal_when_ready)


def _build_page_handler(
    server_url: str,
    *,
    ready_file: Path | None = None,
    no_tray: bool = False,
):
    """Devolve um handler realmente assíncrono para que o Flet aguarde a montagem da página."""

    async def page_handler(page: ft.Page) -> None:
        await desktop_main(
            page,
            server_url,
            ready_file=ready_file,
            no_tray=no_tray,
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

    ready_file = Path(arguments.ready_file).expanduser() if arguments.ready_file.strip() else None
    assets_directory = Path(__file__).resolve().parent / "assets"
    ft.run(
        _build_page_handler(
            server_url,
            ready_file=ready_file,
            no_tray=arguments.no_tray,
        ),
        assets_dir=str(assets_directory),
    )


if __name__ == "__main__":
    main()
