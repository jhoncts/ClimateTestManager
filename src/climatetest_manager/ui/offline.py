"""Tela nativa de consulta usada quando a estação perde o servidor central."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import flet as ft


def _date(value: object) -> str:
    if not isinstance(value, str) or not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    return parsed.strftime("%d/%m/%Y %H:%M")


def _metric(label: str, value: object, icon: ft.IconData) -> ft.Container:
    return ft.Container(
        col={"xs": 6, "md": 3},
        border_radius=14,
        bgcolor="#FFFFFF",
        border=ft.Border.all(1, "#DDE7EE"),
        padding=14,
        content=ft.Row(
            spacing=9,
            controls=[
                ft.Icon(icon, size=20, color="#087E8B"),
                ft.Column(
                    spacing=1,
                    controls=[
                        ft.Text(str(value or 0), size=20, weight=ft.FontWeight.BOLD, color="#0F172A"),
                        ft.Text(label, size=9, color="#64748B"),
                    ],
                ),
            ],
        ),
    )


def _test_card(item: dict[str, Any]) -> ft.Container:
    deadline = item.get("deadline") or "Sem prazo ativo"
    situation = item.get("situation") or "—"
    return ft.Container(
        border_radius=13,
        bgcolor="#FFFFFF",
        border=ft.Border.all(1, "#DDE7EE"),
        padding=14,
        content=ft.ResponsiveRow(
            spacing=10,
            run_spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    col={"xs": 12, "md": 5},
                    content=ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(
                                f"{item.get('client', '—')} / {item.get('process_number', '—')}",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color="#0F172A",
                            ),
                            ft.Text(str(item.get("product", "—")), size=10, color="#64748B"),
                        ],
                    ),
                ),
                ft.Container(
                    col={"xs": 12, "md": 3},
                    content=ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(str(situation), size=10, weight=ft.FontWeight.BOLD, color="#087E8B"),
                            ft.Text(str(deadline), size=9, color="#64748B"),
                        ],
                    ),
                ),
                ft.Container(
                    col={"xs": 12, "md": 4},
                    alignment=ft.Alignment.CENTER_RIGHT,
                    content=ft.Text(
                        f"Retirada: {_date(item.get('nominal_end_at'))}",
                        size=9,
                        color="#64748B",
                        text_align=ft.TextAlign.RIGHT,
                    ),
                ),
            ],
        ),
    )


def build_offline_view(
    snapshot: dict[str, Any] | None,
    *,
    server_url: str,
    on_retry,
) -> ft.Container:
    """Permite consulta ao último estado conhecido e bloqueia qualquer alteração."""

    tests = snapshot.get("tests", []) if snapshot else []
    tests = tests if isinstance(tests, list) else []
    summary = snapshot.get("summary", {}) if snapshot else {}
    summary = summary if isinstance(summary, dict) else {}
    user = snapshot.get("user", {}) if snapshot else {}
    user = user if isinstance(user, dict) else {}
    saved_at = _date(snapshot.get("saved_at")) if snapshot else "Nenhuma sincronização disponível"

    cached_controls = [
        _test_card(item) for item in tests if isinstance(item, dict)
    ] or [
        ft.Container(
            border_radius=14,
            bgcolor="#FFFFFF",
            border=ft.Border.all(1, "#DDE7EE"),
            padding=24,
            alignment=ft.Alignment.CENTER,
            content=ft.Text(
                "Ainda não existe uma cópia local para consulta. Assim que o servidor voltar, "
                "o aplicativo atualizará este cache automaticamente.",
                size=11,
                color="#64748B",
                text_align=ft.TextAlign.CENTER,
            ),
        )
    ]

    return ft.Container(
        expand=True,
        bgcolor="#EEF4F8",
        padding=28,
        content=ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.ResponsiveRow(
                    spacing=12,
                    run_spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            col={"xs": 12, "md": 8},
                            content=ft.Row(
                                spacing=12,
                                controls=[
                                    ft.Container(
                                        width=48,
                                        height=48,
                                        border_radius=14,
                                        bgcolor="#FFFFFF",
                                        padding=3,
                                        content=ft.Image(
                                            src="brand/climatetest-logo.png",
                                            fit=ft.BoxFit.CONTAIN,
                                        ),
                                    ),
                                    ft.Column(
                                        spacing=1,
                                        controls=[
                                            ft.Text(
                                                "ClimateTest Manager — modo offline",
                                                size=20,
                                                weight=ft.FontWeight.BOLD,
                                                color="#0F172A",
                                            ),
                                            ft.Text(
                                                "Consulta do último estado sincronizado • nenhuma alteração é permitida",
                                                size=10,
                                                color="#64748B",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            col={"xs": 12, "md": 4},
                            alignment=ft.Alignment.CENTER_RIGHT,
                            content=ft.Button(
                                content="Tentar reconectar",
                                icon=ft.Icons.SYNC,
                                bgcolor="#087E8B",
                                color="#FFFFFF",
                                on_click=on_retry,
                            ),
                        ),
                    ],
                ),
                ft.Container(
                    border_radius=13,
                    bgcolor="#FFF4D6",
                    border=ft.Border.all(1, "#F0C86A"),
                    padding=12,
                    content=ft.Row(
                        spacing=9,
                        controls=[
                            ft.Icon(ft.Icons.WIFI_OFF, color="#A66505", size=19),
                            ft.Text(
                                f"Sem comunicação com {server_url}. O aplicativo continuará tentando "
                                "reconectar em segundo plano. Não feche o servidor para trabalhar offline.",
                                expand=True,
                                size=10,
                                color="#69420A",
                            ),
                        ],
                    ),
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    wrap=True,
                    run_spacing=4,
                    controls=[
                        ft.Text(
                            f"Última sincronização: {saved_at}",
                            size=10,
                            color="#64748B",
                        ),
                        ft.Text(
                            f"Sessão: {user.get('name', '—')} • {user.get('role', '—')}",
                            size=10,
                            color="#64748B",
                        ),
                    ],
                ),
                ft.ResponsiveRow(
                    spacing=10,
                    run_spacing=10,
                    controls=[
                        _metric("Em andamento", summary.get("in_progress", 0), ft.Icons.PLAY_CIRCLE_OUTLINE),
                        _metric("Aguardando", summary.get("waiting", 0), ft.Icons.PENDING_ACTIONS),
                        _metric("Pausados", summary.get("paused", 0), ft.Icons.PAUSE_CIRCLE_OUTLINE),
                        _metric("Atrasados", summary.get("overdue", 0), ft.Icons.WARNING_AMBER),
                    ],
                ),
                ft.Text(
                    "Ensaios salvos para consulta",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color="#0F172A",
                ),
                *cached_controls,
                ft.Container(height=8),
            ],
        ),
    )
