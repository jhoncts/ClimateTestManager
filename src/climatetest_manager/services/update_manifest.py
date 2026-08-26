"""Construção determinística do manifesto de atualização estável."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

_VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+")
_BUILD_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().lower()


def create_manifest(
    *,
    version: str,
    build_revision: str,
    installer: Path,
    repository: str,
    tag: str,
    release_notes: str = "",
    mandatory: bool = False,
    signer_subject: str = "",
    signer_thumbprint: str = "",
    published_at: str = "",
) -> dict[str, object]:
    normalized_version = version.strip().removeprefix("v")
    if not _VERSION_PATTERN.fullmatch(normalized_version):
        raise ValueError("A versão deve usar o formato X.Y.Z.")
    if not _BUILD_PATTERN.fullmatch(build_revision.strip()):
        raise ValueError("A revisão de build é inválida.")
    expected_name = f"ClimateTestManager-Setup-v{normalized_version}.exe"
    if installer.name != expected_name or not installer.is_file():
        raise ValueError(f"O instalador esperado não foi encontrado: {expected_name}")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository.strip()):
        raise ValueError("O repositório deve usar o formato proprietário/projeto.")
    normalized_tag = tag.strip()
    if not normalized_tag:
        raise ValueError("A tag da Release não foi informada.")

    normalized_thumbprint = re.sub(r"\s+", "", signer_thumbprint).upper()
    if normalized_thumbprint and not re.fullmatch(
        r"(?:[0-9A-F]{40}|[0-9A-F]{64})", normalized_thumbprint
    ):
        raise ValueError("A impressão digital do certificado é inválida.")

    release_root = f"https://github.com/{repository.strip()}/releases"
    manifest: dict[str, object] = {
        "schema": 1,
        "product": "ClimateTestManager",
        "channel": "stable",
        "version": normalized_version,
        "build_revision": build_revision.strip(),
        "published_at": published_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "mandatory": mandatory,
        "release_url": f"{release_root}/tag/{normalized_tag}",
        "release_notes": release_notes.strip(),
        "installer": {
            "name": expected_name,
            "url": f"{release_root}/download/{normalized_tag}/{expected_name}",
            "size": installer.stat().st_size,
            "sha256": _sha256(installer),
        },
    }
    if normalized_thumbprint:
        manifest["signer"] = {
            "subject": signer_subject.strip(),
            "thumbprint": normalized_thumbprint,
        }
    return manifest
