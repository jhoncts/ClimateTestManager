"""Ponte entre a sessão hospedada no servidor e o cliente Windows local."""

from __future__ import annotations

import json
import time
from typing import Any

import flet as ft

TOAST_COMMAND_KEY = "climatetest.manager.desktop.toast-command.v1"
THEME_PREFERENCE_KEY = "climatetest.manager.desktop.theme.v2"
OFFLINE_SNAPSHOT_KEY = "climatetest.manager.desktop.offline-snapshot.v1"


async def queue_desktop_toast(
    page: ft.Page,
    *,
    title: str,
    message: str,
    launch: str = "climatetest://open",
) -> None:
    """Solicita ao wrapper desktop a exibição de um toast no Windows."""

    payload = {
        "id": str(time.time_ns()),
        "title": title,
        "message": message,
        "launch": launch,
    }
    await page.shared_preferences.set(TOAST_COMMAND_KEY, json.dumps(payload, ensure_ascii=False))


async def load_local_theme(page: ft.Page, default: str = "light") -> str:
    value = await page.shared_preferences.get(THEME_PREFERENCE_KEY)
    if isinstance(value, str) and value.strip():
        return value.strip().casefold()
    return default


async def save_local_theme(page: ft.Page, mode: str) -> None:
    """Persiste a aparência apenas no dispositivo do usuário atual."""

    await page.shared_preferences.set(THEME_PREFERENCE_KEY, mode.strip().casefold())


async def save_offline_snapshot(page: ft.Page, payload: dict[str, Any]) -> None:
    """Guarda uma fotografia de consulta no dispositivo sem permitir escrita offline."""

    await page.shared_preferences.set(
        OFFLINE_SNAPSHOT_KEY,
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )


async def load_offline_snapshot(page: ft.Page) -> dict[str, Any] | None:
    raw = await page.shared_preferences.get(OFFLINE_SNAPSHOT_KEY)
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return result if isinstance(result, dict) else None
