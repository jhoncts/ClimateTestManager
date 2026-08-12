"""Conversão explícita dos registros UTC para o horário operacional local."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "America/Sao_Paulo"


def local_timezone() -> ZoneInfo:
    name = os.getenv("CLIMATETEST_TIMEZONE", DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TIMEZONE)


def to_local_datetime(value: datetime, *, assume_utc: bool = False) -> datetime:
    """Converte um instante para o fuso do laboratório sem alterar horários locais ingênuos."""

    if value.tzinfo is None:
        if not assume_utc:
            return value
        value = value.replace(tzinfo=UTC)
    return value.astimezone(local_timezone()).replace(tzinfo=None)


def format_local_datetime(value: datetime | None, *, assume_utc: bool = False) -> str:
    if value is None:
        return "—"
    return to_local_datetime(value, assume_utc=assume_utc).strftime("%d/%m/%Y %H:%M")
