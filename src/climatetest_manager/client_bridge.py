"""Mensagens leves entre a sessão Flet remota e o host desktop da estação."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import flet as ft

TOAST_COMMAND_KEY = "climatetest.manager.desktop.toast-command.v1"
TOAST_CURSOR_KEY = "climatetest.manager.desktop.toast-cursor.v1"
THEME_PREFERENCE_KEY = "climatetest.manager.desktop.theme.v2"
OFFLINE_SNAPSHOT_KEY = "climatetest.manager.desktop.offline-snapshot.v1"


@dataclass(frozen=True, slots=True)
class DesktopToastCommand:
    command_id: str
    title: str
    message: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "id": self.command_id,
                "title": self.title,
                "message": self.message,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, value: str) -> DesktopToastCommand:
        payload = json.loads(value)
        if not isinstance(payload, dict):
            raise ValueError("Comando de notificação inválido.")
        command_id = str(payload.get("id", "")).strip()
        title = str(payload.get("title", "")).strip()
        message = str(payload.get("message", "")).strip()
        if not command_id or not title or not message:
            raise ValueError("Comando de notificação incompleto.")
        return cls(command_id=command_id, title=title, message=message)


async def queue_desktop_toast(
    page: ft.Page,
    title: str,
    message: str,
    *,
    command_id: str | None = None,
) -> bool:
    """Entrega um comando ao armazenamento local do dispositivo conectado."""

    identifier = command_id or f"manual-{time.time_ns()}"
    command = DesktopToastCommand(
        command_id=identifier,
        title=title.strip() or "ClimateTest Manager",
        message=message.strip() or "Novo aviso disponível.",
    )
    try:
        return bool(await page.shared_preferences.set(TOAST_COMMAND_KEY, command.to_json()))
    except Exception:
        return False


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
