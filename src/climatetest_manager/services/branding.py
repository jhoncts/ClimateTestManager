"""Localização dos recursos visuais no código-fonte e nos executáveis empacotados."""

from __future__ import annotations

import sys
from pathlib import Path


def asset_path(relative_path: str) -> Path:
    """Resolve um asset no desenvolvimento e dentro do diretório temporário do PyInstaller."""

    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        bundled = Path(bundle_root) / "assets" / relative_path
        if bundled.exists():
            return bundled
    return Path(__file__).resolve().parents[2] / "assets" / relative_path


def brand_logo_path() -> Path:
    return asset_path("brand/climatetest-logo.png")
