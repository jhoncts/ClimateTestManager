"""Mensagens leves entre a sessão Flet remota e o host desktop da estação."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

import flet as ft

TOAST_COMMAND_KEY = "climatetest.manager.desktop.toast-command.v1"
TOAST_CURSOR_KEY = "climatetest.manager.desktop.toast-cursor.v1"


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
    def from_json(cls, value: str) -> "DesktopToastCommand":
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
