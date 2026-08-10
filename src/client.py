"""Cliente desktop nativo que conecta ao servidor central do ClimateTest Manager."""

import argparse
import asyncio
import urllib.error
import urllib.request
from pathlib import Path

import flet as ft

VERSION = "0.7.0"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--url", default="http://localhost:8550")
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args()


def _server_available(server_url: str, *, timeout: float = 1.5) -> bool:
    try:
        request = urllib.request.Request(server_url, method="GET")
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
    page.window.icon = "brand/climatetest-logo.png"


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


async def desktop_main(page: ft.Page, server_url: str) -> None:
    """Mantém o servidor invisível e mostra somente uma janela própria do aplicativo."""

    _configure_page(page)
    server_url = server_url.rstrip("/")
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

    embedded_app = ft.Container(
        expand=True,
        opacity=0,
        animate_opacity=280,
        content=ft.FletApp(
            url=server_url,
            expand=True,
            reconnect_interval_ms=1500,
            reconnect_timeout_ms=30000,
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
                "Servidor indisponível. Confirme se o computador central está ligado "
                "e conectado à rede. Código CTM-CLI-001."
            )
            status.color = "#B42318"
            retry.visible = True
            page.update()
            return

        status.value = "Servidor encontrado. Abrindo o ClimateTest Manager..."
        status.color = "#087E8B"
        page.update()
        await asyncio.sleep(0.65)
        embedded_app.opacity = 1
        splash.opacity = 0
        page.update()
        await asyncio.sleep(0.32)
        splash.visible = False
        page.update()

    page.run_task(reveal_when_ready)


def main() -> None:
    arguments = _arguments()
    server_url = arguments.url.rstrip("/")
    if arguments.check_only:
        raise SystemExit(0 if _server_available(server_url, timeout=3) else 20)

    assets_directory = Path(__file__).resolve().parent / "assets"
    ft.run(
        lambda page: desktop_main(page, server_url),
        assets_dir=str(assets_directory),
    )


if __name__ == "__main__":
    main()
