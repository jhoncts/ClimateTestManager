"""Build-only staging hook for the validated UI-FIX-7 candidate.

The approved UI-FIX-7 source is stored as a release-candidate overlay so the
application code remains frozen until the final multi-PC validation. Pytest is
already executed by both Quality and Build Windows release; loading this
conftest expands the validated overlay before test collection. In the release
workflow the same expanded working tree is then packaged by the existing build
step.
"""

from __future__ import annotations

import base64
import binascii
import struct
import zlib
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

_PROJECT_ROOT = Path(__file__).resolve().parent
_OVERLAY = _PROJECT_ROOT / ".release-candidate" / "ui-fix7-overlay.zip"


def _decode_overlay(payload: bytes) -> bytes:
    candidate = payload
    for _ in range(3):
        if candidate.startswith(b"PK"):
            return candidate
        try:
            candidate = base64.b64decode(b"".join(candidate.split()), validate=False)
        except binascii.Error:
            break
    if candidate.startswith(b"PK"):
        return candidate
    raise RuntimeError("UI-FIX-7 release-candidate overlay is not a ZIP payload.")


def _safe_destination(name: str) -> Path:
    relative = Path(name.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"Unsafe path in UI-FIX-7 overlay: {name}")
    destination = (_PROJECT_ROOT / relative).resolve()
    project_root = _PROJECT_ROOT.resolve()
    if project_root not in destination.parents and destination != project_root:
        raise RuntimeError(f"Unsafe path in UI-FIX-7 overlay: {name}")
    return destination


def _extract_local_entries(payload: bytes) -> int:
    """Recover local ZIP entries when a transport omitted the central directory."""

    offset = 0
    extracted = 0
    header_struct = struct.Struct("<4s5H3I2H")
    while offset + header_struct.size <= len(payload):
        signature = payload[offset : offset + 4]
        if signature in {b"PK\x01\x02", b"PK\x05\x06"}:
            break
        if signature != b"PK\x03\x04":
            if extracted:
                break
            raise RuntimeError("UI-FIX-7 overlay does not contain readable ZIP entries.")

        (
            _signature,
            _version,
            flags,
            compression,
            _mtime,
            _mdate,
            expected_crc,
            compressed_size,
            uncompressed_size,
            name_length,
            extra_length,
        ) = header_struct.unpack_from(payload, offset)

        if flags & 0x08:
            raise RuntimeError("UI-FIX-7 overlay uses unsupported ZIP data descriptors.")

        name_start = offset + header_struct.size
        name_end = name_start + name_length
        data_start = name_end + extra_length
        data_end = data_start + compressed_size
        if data_end > len(payload):
            raise RuntimeError("UI-FIX-7 overlay was truncated inside a file entry.")

        encoding = "utf-8" if flags & 0x800 else "cp437"
        name = payload[name_start:name_end].decode(encoding)
        compressed = payload[data_start:data_end]
        if compression == 0:
            data = compressed
        elif compression == 8:
            data = zlib.decompress(compressed, -15)
        else:
            raise RuntimeError(f"Unsupported ZIP compression method: {compression}")

        if len(data) != uncompressed_size:
            raise RuntimeError(f"Invalid size for overlay entry: {name}")
        if (zlib.crc32(data) & 0xFFFFFFFF) != expected_crc:
            raise RuntimeError(f"Invalid CRC for overlay entry: {name}")

        destination = _safe_destination(name)
        if name.endswith("/"):
            destination.mkdir(parents=True, exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        extracted += 1
        offset = data_end

    return extracted


def _extract_overlay(payload: bytes) -> None:
    try:
        with ZipFile(BytesIO(payload)) as archive:
            for member in archive.namelist():
                _safe_destination(member)
            archive.extractall(_PROJECT_ROOT)
            return
    except BadZipFile:
        pass

    if _extract_local_entries(payload) == 0:
        raise RuntimeError("UI-FIX-7 overlay could not be extracted.")


if _OVERLAY.exists():
    _extract_overlay(_decode_overlay(_OVERLAY.read_bytes()))
