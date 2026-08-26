"""Atualizações verificadas do aplicativo Windows a partir de uma publicação global."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from platformdirs import user_cache_path

DEFAULT_REPOSITORY = "jhoncts/ClimateTestManager"
DEFAULT_MANIFEST_URL = (
    "https://github.com/jhoncts/ClimateTestManager/releases/latest/download/update-manifest.json"
)
DEFAULT_UPDATE_INTERVAL_SECONDS = 6 * 60 * 60
MANIFEST_SCHEMA_VERSION = 1
_USER_AGENT = "ClimateTestManager-Updater"
_HASH_PATTERN = re.compile(r"\b([0-9a-fA-F]{64})\b")
_BUILD_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
_TRUSTED_DOWNLOAD_HOSTS = {
    "github.com",
    "api.github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
}
_MAX_INSTALLER_BYTES = 1_500_000_000


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    """Metadados necessários para conferir e instalar uma atualização."""

    version: str
    installer_url: str
    installer_name: str
    expected_sha256: str | None
    checksum_url: str | None
    release_notes: str = ""
    build_revision: str = ""
    release_url: str = ""
    expected_size: int | None = None
    mandatory: bool = False
    signer_subject: str = ""
    signer_thumbprint: str = ""
    source: str = "github-release"


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


def _validated_https_url(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} não informado.")
    normalized = value.strip()
    parsed = urlsplit(normalized)
    if (
        parsed.scheme.casefold() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(f"{label} deve usar HTTPS.")
    if parsed.hostname.casefold() not in _TRUSTED_DOWNLOAD_HOSTS:
        raise ValueError(f"{label} não pertence ao canal oficial de atualização.")
    return normalized


def _request_json(url: str, *, timeout: float, github_api: bool = False) -> dict[str, object]:
    headers = {
        "Accept": "application/vnd.github+json" if github_api else "application/json",
        "User-Agent": _USER_AGENT,
    }
    if github_api:
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers)
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


def _asset_size(asset: object) -> int | None:
    if not isinstance(asset, dict):
        return None
    value = asset.get("size")
    return value if isinstance(value, int) and 0 < value <= _MAX_INSTALLER_BYTES else None


def parse_release_payload(payload: dict[str, object], *, current_version: str) -> UpdateInfo | None:
    """Compatibilidade com clientes antigos usando a API pública de Releases."""

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
    expected_installer_key = expected_installer.casefold()
    installer_asset = next(
        (asset for asset in assets if _asset_name(asset).casefold() == expected_installer_key),
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
    try:
        installer_url = _validated_https_url(installer_url, label="URL do instalador")
    except ValueError:
        return None
    notes = payload.get("body")
    release_url = payload.get("html_url")
    return UpdateInfo(
        version=version,
        installer_url=installer_url,
        installer_name=expected_installer,
        expected_sha256=_asset_digest(installer_asset),
        checksum_url=_asset_url(checksum_asset) if checksum_asset is not None else None,
        release_notes=notes.strip() if isinstance(notes, str) else "",
        release_url=release_url.strip() if isinstance(release_url, str) else "",
        expected_size=_asset_size(installer_asset),
    )


def parse_update_manifest(payload: dict[str, object], *, current_version: str) -> UpdateInfo | None:
    """Valida o manifesto estável publicado junto com o instalador."""

    if payload.get("schema") != MANIFEST_SCHEMA_VERSION:
        raise ValueError("Versão do manifesto de atualização não suportada.")
    if payload.get("product") != "ClimateTestManager":
        raise ValueError("O manifesto pertence a outro produto.")
    if payload.get("channel") != "stable":
        raise ValueError("O manifesto não pertence ao canal estável.")

    version_value = payload.get("version")
    if not isinstance(version_value, str):
        raise ValueError("Versão ausente no manifesto.")
    version = version_value.strip().removeprefix("v")
    _version_tuple(version)
    if not is_newer_version(version, current_version):
        return None

    build_value = payload.get("build_revision")
    if not isinstance(build_value, str) or not _BUILD_PATTERN.fullmatch(build_value.strip()):
        raise ValueError("Revisão de build inválida no manifesto.")
    build_revision = build_value.strip()

    installer = payload.get("installer")
    if not isinstance(installer, dict):
        raise ValueError("Instalador ausente no manifesto.")
    expected_name = f"ClimateTestManager-Setup-v{version}.exe"
    if installer.get("name") != expected_name:
        raise ValueError("Nome do instalador não corresponde à versão publicada.")
    installer_url = _validated_https_url(installer.get("url"), label="URL do instalador")

    digest = installer.get("sha256")
    if not isinstance(digest, str) or not _HASH_PATTERN.fullmatch(digest.strip()):
        raise ValueError("SHA-256 inválido no manifesto.")
    expected_hash = digest.strip().lower()

    size = installer.get("size")
    if not isinstance(size, int) or not 0 < size <= _MAX_INSTALLER_BYTES:
        raise ValueError("Tamanho do instalador inválido no manifesto.")

    notes = payload.get("release_notes")
    release_url_value = payload.get("release_url")
    release_url = ""
    if isinstance(release_url_value, str) and release_url_value.strip():
        release_url = _validated_https_url(release_url_value, label="URL da publicação")

    signer = payload.get("signer")
    signer_subject = ""
    signer_thumbprint = ""
    if signer is not None:
        if not isinstance(signer, dict):
            raise ValueError("Assinatura inválida no manifesto.")
        raw_subject = signer.get("subject")
        raw_thumbprint = signer.get("thumbprint")
        if isinstance(raw_subject, str):
            signer_subject = raw_subject.strip()
        if isinstance(raw_thumbprint, str):
            signer_thumbprint = re.sub(r"\s+", "", raw_thumbprint).upper()
        if signer_thumbprint and not re.fullmatch(
            r"(?:[0-9A-F]{40}|[0-9A-F]{64})", signer_thumbprint
        ):
            raise ValueError("Impressão digital da assinatura inválida.")

    mandatory = payload.get("mandatory", False)
    if not isinstance(mandatory, bool):
        raise ValueError("Indicador de atualização obrigatória inválido.")

    return UpdateInfo(
        version=version,
        build_revision=build_revision,
        installer_url=installer_url,
        installer_name=expected_name,
        expected_sha256=expected_hash,
        checksum_url=None,
        release_notes=notes.strip() if isinstance(notes, str) else "",
        release_url=release_url,
        expected_size=size,
        mandatory=mandatory,
        signer_subject=signer_subject,
        signer_thumbprint=signer_thumbprint,
        source="signed-manifest" if signer_thumbprint else "manifest",
    )


def check_for_update(
    current_version: str,
    *,
    repository: str = DEFAULT_REPOSITORY,
    manifest_url: str | None = None,
    timeout: float = 4.0,
) -> UpdateInfo | None:
    """Consulta o manifesto global e mantém fallback para Releases antigas."""

    selected_manifest = (
        manifest_url
        or os.environ.get("CLIMATETEST_UPDATE_MANIFEST_URL", "").strip()
        or DEFAULT_MANIFEST_URL
    )
    try:
        selected_manifest = _validated_https_url(selected_manifest, label="URL do manifesto")
        payload = _request_json(selected_manifest, timeout=timeout)
        return parse_update_manifest(payload, current_version=current_version)
    except (OSError, urllib.error.URLError, ValueError, json.JSONDecodeError):
        pass

    url = f"https://api.github.com/repos/{repository}/releases/latest"
    try:
        payload = _request_json(url, timeout=timeout, github_api=True)
        return parse_release_payload(payload, current_version=current_version)
    except (OSError, urllib.error.URLError, ValueError, json.JSONDecodeError):
        return None


def _download_bytes(url: str, *, timeout: float = 15.0) -> bytes:
    _validated_https_url(url, label="URL do checksum")
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().lower()


def _verify_authenticode_signature(installer: Path, update: UpdateInfo) -> None:
    """Confere a assinatura declarada quando a Release já usa certificado comercial."""

    if sys.platform != "win32" or not update.signer_thumbprint:
        return
    script = (
        "$s=Get-AuthenticodeSignature -LiteralPath $args[0];"
        "$o=[ordered]@{status=[string]$s.Status;subject='';thumbprint=''};"
        "if($s.SignerCertificate){$o.subject=$s.SignerCertificate.Subject;"
        "$o.thumbprint=$s.SignerCertificate.Thumbprint};"
        "$o|ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
            str(installer),
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=20,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        result = json.loads(completed.stdout)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("O Windows não conseguiu validar a assinatura do instalador.") from error
    actual_thumbprint = re.sub(r"\s+", "", str(result.get("thumbprint", ""))).upper()
    if result.get("status") != "Valid" or actual_thumbprint != update.signer_thumbprint:
        raise ValueError("A assinatura digital do instalador não corresponde à publicação.")


def download_verified_update(update: UpdateInfo) -> Path:
    """Baixa o EXE e valida tamanho, SHA-256 e, quando disponível, Authenticode."""

    installer_url = _validated_https_url(update.installer_url, label="URL do instalador")
    expected_hash = _resolve_expected_hash(update)
    destination_directory = (
        user_cache_path("ClimateTestManager", "ClimateTestManager", ensure_exists=False)
        / "updates"
        / f"v{update.version}"
    )
    destination_directory.mkdir(parents=True, exist_ok=True)
    destination = destination_directory / update.installer_name
    temporary = destination.with_suffix(destination.suffix + ".download")

    if destination.is_file():
        size_matches = (
            update.expected_size is None or destination.stat().st_size == update.expected_size
        )
        if size_matches and _sha256(destination) == expected_hash:
            _verify_authenticode_signature(destination, update)
            return destination
        destination.unlink(missing_ok=True)

    temporary.unlink(missing_ok=True)
    actual_size = 0
    digest = hashlib.sha256()
    try:
        with (
            urllib.request.urlopen(
                urllib.request.Request(installer_url, headers={"User-Agent": _USER_AGENT}),
                timeout=30,
            ) as response,
            temporary.open("wb") as output,
        ):
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                actual_size += len(chunk)
                if actual_size > _MAX_INSTALLER_BYTES:
                    raise ValueError("O instalador excede o tamanho máximo permitido.")
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    if update.expected_size is not None and actual_size != update.expected_size:
        temporary.unlink(missing_ok=True)
        raise ValueError("O tamanho do instalador não corresponde ao manifesto publicado.")
    if digest.hexdigest().lower() != expected_hash:
        temporary.unlink(missing_ok=True)
        raise ValueError(
            "O instalador baixado não corresponde ao SHA-256 publicado. "
            "A atualização foi cancelada por segurança."
        )
    _verify_authenticode_signature(temporary, update)
    temporary.replace(destination)
    return destination


def installed_role_and_server() -> tuple[str, str]:
    """Lê o papel persistido pelo instalador sem depender do servidor estar online."""

    root = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "ClimateTestManager"
    if (root / "server-mode.marker").is_file():
        return "server", "http://localhost:8550"
    role = "client" if (root / "client-mode.marker").is_file() else ""
    try:
        server_url = (root / "server.url").read_text(encoding="utf-8").strip()
    except OSError:
        server_url = ""
    return role, server_url


def launch_installer_elevated(
    installer: Path,
    *,
    role: str = "",
    server_address: str = "",
) -> bool:
    """Pede UAC e atualiza silenciosamente, preservando o papel da instalação."""

    if sys.platform != "win32" or not installer.is_file():
        return False
    selected_role = role.strip().casefold()
    selected_server = server_address.strip()
    if not selected_role:
        selected_role, selected_server = installed_role_and_server()
    if selected_role not in {"", "server", "client"}:
        raise ValueError("Papel local inválido para atualização.")

    arguments = ["/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-"]
    if selected_role:
        arguments.append(f"/ROLE={selected_role}")
    if selected_role == "client" and selected_server:
        arguments.append(f"/SERVERADDRESS={selected_server}")
    log_directory = (
        Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "ClimateTestManager" / "Logs"
    )
    try:
        log_directory.mkdir(parents=True, exist_ok=True)
        arguments.append(f'/LOG="{log_directory / "automatic-update.log"}"')
    except OSError:
        pass

    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        str(installer),
        subprocess.list2cmdline(arguments),
        str(installer.parent),
        1,
    )
    return int(result) > 32


def automatic_update_checks_enabled() -> bool:
    return (
        os.environ.get("CLIMATETEST_DISABLE_UPDATE_CHECK", "").strip() != "1"
        and os.environ.get("GITHUB_ACTIONS", "").casefold() != "true"
    )


def central_update_checks_enabled() -> bool:
    """Permite avisos do GitHub somente no servidor central administrado pelo TI."""

    if not automatic_update_checks_enabled():
        return False
    role, _server_address = installed_role_and_server()
    return role == "server"


def update_check_interval_seconds() -> int:
    """Intervalo configurável, limitado entre 15 minutos e 24 horas."""

    raw = os.environ.get("CLIMATETEST_UPDATE_INTERVAL_SECONDS", "").strip()
    try:
        configured = int(raw) if raw else DEFAULT_UPDATE_INTERVAL_SECONDS
    except ValueError:
        configured = DEFAULT_UPDATE_INTERVAL_SECONDS
    return max(15 * 60, min(configured, 24 * 60 * 60))
