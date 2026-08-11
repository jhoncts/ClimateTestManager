"""Atualizações verificadas do aplicativo Windows a partir de GitHub Releases."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_cache_path

DEFAULT_REPOSITORY = "jhoncts/ClimateTestManager"
_USER_AGENT = "ClimateTestManager-Updater"
_HASH_PATTERN = re.compile(r"\b([0-9a-fA-F]{64})\b")


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    """Metadados mínimos necessários para uma atualização verificável."""

    version: str
    installer_url: str
    installer_name: str
    expected_sha256: str | None
    checksum_url: str | None
    release_notes: str = ""


def _version_tuple(value: str) -> tuple[int, ...]:
    """Compara versões numéricas simples sem depender de bibliotecas extras."""

    normalized = value.strip().lower().removeprefix("v")
    parts = normalized.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        raise ValueError(f"Versão inválida: {value}")
    return tuple(int(part) for part in parts)


def is_newer_version(candidate: str, current: str) -> bool:
    try:
        return _version_tuple(candidate) > _version_tuple(current)
    except ValueError:
        return False


def _request_json(url: str, *, timeout: float) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": _USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Resposta de atualização inválida.")
    return payload


def _asset_url(asset: object) -> str:
    if not isinstance(asset, dict):
        return ""
    value = asset.get("browser_download_url")
    return value if isinstance(value, str) else ""


def _asset_name(asset: object) -> str:
    if not isinstance(asset, dict):
        return ""
    value = asset.get("name")
    return value if isinstance(value, str) else ""


def _asset_digest(asset: object) -> str | None:
    if not isinstance(asset, dict):
        return None
    value = asset.get("digest")
    if not isinstance(value, str) or not value.lower().startswith("sha256:"):
        return None
    digest = value.split(":", 1)[1].strip().lower()
    return digest if _HASH_PATTERN.fullmatch(digest) else None


def parse_release_payload(payload: dict[str, object], *, current_version: str) -> UpdateInfo | None:
    """Seleciona apenas uma release publicada, mais nova e com instalador Windows."""

    if payload.get("draft") is True or payload.get("prerelease") is True:
        return None
    tag_name = payload.get("tag_name")
    if not isinstance(tag_name, str):
        return None
    version = tag_name.strip().removeprefix("v")
    if not is_newer_version(version, current_version):
        return None

    assets = payload.get("assets")
    if not isinstance(assets, list):
        return None
    expected_installer = f"ClimateTestManager-Setup-v{version}.exe"
    installer_asset = next(
        (asset for asset in assets if _asset_name(asset).casefold() == expected_installer.casefold()),
        None,
    )
    if installer_asset is None:
        return None

    checksum_names = {
        f"ClimateTestManager-Setup-v{version}-SHA256.txt".casefold(),
        f"ClimateTestManager-Setup-v{version}.exe.sha256".casefold(),
    }
    checksum_asset = next(
        (asset for asset in assets if _asset_name(asset).casefold() in checksum_names),
        None,
    )
    installer_url = _asset_url(installer_asset)
    if not installer_url:
        return None
    notes = payload.get("body")
    return UpdateInfo(
        version=version,
        installer_url=installer_url,
        installer_name=expected_installer,
        expected_sha256=_asset_digest(installer_asset),
        checksum_url=_asset_url(checksum_asset) if checksum_asset is not None else None,
        release_notes=notes.strip() if isinstance(notes, str) else "",
    )


def check_for_update(
    current_version: str,
    *,
    repository: str = DEFAULT_REPOSITORY,
    timeout: float = 4.0,
) -> UpdateInfo | None:
    """Consulta a última release pública; falhas de internet não afetam o aplicativo."""

    url = f"https://api.github.com/repos/{repository}/releases/latest"
    try:
        payload = _request_json(url, timeout=timeout)
        return parse_release_payload(payload, current_version=current_version)
    except (OSError, urllib.error.URLError, ValueError, json.JSONDecodeError):
        return None


def _download_bytes(url: str, *, timeout: float = 15.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _resolve_expected_hash(update: UpdateInfo) -> str:
    if update.expected_sha256:
        return update.expected_sha256.lower()
    if not update.checksum_url:
        raise ValueError("A atualização publicada não possui SHA-256 para validação.")
    content = _download_bytes(update.checksum_url).decode("ascii", errors="ignore")
    match = _HASH_PATTERN.search(content)
    if match is None:
        raise ValueError("O arquivo SHA-256 da atualização é inválido.")
    return match.group(1).lower()


def download_verified_update(update: UpdateInfo) -> Path:
    """Baixa em arquivo temporário e só publica o EXE depois de conferir o SHA-256."""

    expected_hash = _resolve_expected_hash(update)
    destination_directory = (
        user_cache_path("ClimateTestManager", "ClimateTestManager", ensure_exists=False)
        / "updates"
        / f"v{update.version}"
    )
    destination_directory.mkdir(parents=True, exist_ok=True)
    destination = destination_directory / update.installer_name
    temporary = destination.with_suffix(destination.suffix + ".download")
    with urllib.request.urlopen(
        urllib.request.Request(update.installer_url, headers={"User-Agent": _USER_AGENT}),
        timeout=30,
    ) as response, temporary.open("wb") as output:
        digest = hashlib.sha256()
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            output.write(chunk)

    actual_hash = digest.hexdigest().lower()
    if actual_hash != expected_hash:
        temporary.unlink(missing_ok=True)
        raise ValueError(
            "O instalador baixado não corresponde ao SHA-256 publicado. "
            "A atualização foi cancelada por segurança."
        )
    temporary.replace(destination)
    return destination


def launch_installer_elevated(installer: Path) -> bool:
    """Pede UAC no Windows e deixa o instalador existente preservar papel/configuração."""

    if sys.platform != "win32" or not installer.is_file():
        return False
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        str(installer),
        "/NORESTART",
        str(installer.parent),
        1,
    )
    return int(result) > 32


def automatic_update_checks_enabled() -> bool:
    return (
        os.environ.get("CLIMATETEST_DISABLE_UPDATE_CHECK", "").strip() != "1"
        and os.environ.get("GITHUB_ACTIONS", "").casefold() != "true"
    )
