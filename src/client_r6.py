"""Cliente R6 com verificação explícita da versão do servidor central."""

from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path

import flet as ft

import client as legacy

APP_VERSION = "0.8.2"
BUILD_REVISION = "R6-20260813"
BUILD_MARKER_PATH = "/server-build.txt"

# A infraestrutura validada de janela, bandeja, atualização e reconexão é mantida.
legacy.VERSION = APP_VERSION


def _server_build(server_url: str, *, timeout: float = 2.0) -> str:
    request = urllib.request.Request(
        server_url.rstrip("/") + BUILD_MARKER_PATH,
        method="GET",
        headers={"User-Agent": f"ClimateTestManager/{APP_VERSION}-{BUILD_REVISION}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if not (200 <= response.status < 300):
                return ""
            return response.read(128).decode("utf-8", errors="replace").strip()
    except (OSError, urllib.error.URLError, ValueError):
        return ""


def _diagnostic_page(page: ft.Page, server_url: str, found_build: str) -> None:
    legacy._configure_page(page)
    found = found_build or "versão antiga/sem identificação"
    page.add(
        ft.Container(
            expand=True,
            bgcolor="#EDF3F8",
            alignment=ft.Alignment.CENTER,
            content=ft.Container(
                width=620,
                padding=34,
                border_radius=22,
                bgcolor="#FFFFFF",
                content=ft.Column(
                    tight=True,
                    spacing=14,
                    controls=[
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=42, color="#B7791F"),
                        ft.Text(
                            "Servidor central desatualizado",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color="#102A43",
                        ),
                        ft.Text(
                            "Esta estação está com a versão 0.8.2, mas o computador central "
                            "ainda não está executando a mesma interface validada. Para evitar "
                            "telas antigas ou inconsistentes, a conexão foi bloqueada.",
                            size=13,
                            color="#536579",
                        ),
                        ft.Container(
                            border_radius=12,
                            bgcolor="#FFF7E6",
                            padding=14,
                            content=ft.Column(
                                spacing=5,
                                controls=[
                                    ft.Text(
                                        f"Servidor: {server_url}",
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                        color="#102A43",
                                    ),
                                    ft.Text(
                                        f"Esperado: {BUILD_REVISION}",
                                        size=11,
                                        color="#536579",
                                    ),
                                    ft.Text(
                                        f"Encontrado: {found}",
                                        size=11,
                                        color="#536579",
                                    ),
                                ],
                            ),
                        ),
                        ft.Text(
                            "Instale primeiro o mesmo instalador no computador servidor, "
                            "escolhendo “Servidor central”. Depois abra esta estação novamente.",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color="#B42318",
                        ),
                        ft.Text(
                            f"Cliente desktop {APP_VERSION} • build {BUILD_REVISION}",
                            size=10,
                            color="#8292A3",
                        ),
                    ],
                ),
            ),
        )
    )


def main() -> None:
    legacy._enable_high_dpi()
    arguments = legacy._arguments()
    try:
        server_url = legacy._resolve_server_url(arguments.url)
    except ValueError:
        raise SystemExit(21) from None

    reachable = legacy._server_available(server_url, timeout=2.5)
    build = _server_build(server_url, timeout=2.5) if reachable else ""

    if arguments.check_only:
        if not reachable:
            raise SystemExit(20)
        raise SystemExit(0 if build == BUILD_REVISION else 22)

    if reachable and build != BUILD_REVISION:
        ft.run(
            lambda page: _diagnostic_page(page, server_url, build),
            assets_dir=str(Path(__file__).resolve().parent / "assets"),
        )
        return

    legacy.main()


if __name__ == "__main__":
    main()
