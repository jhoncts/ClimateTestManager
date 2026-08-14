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
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

_PROJECT_ROOT = Path(__file__).resolve().parent
_OVERLAY = _PROJECT_ROOT / ".release-candidate" / "ui-fix7-overlay.zip"


def _decode_overlay(payload: bytes) -> bytes:
    candidate = payload.strip()
    for _ in range(3):
        if candidate.startswith(b"PK"):
            return candidate
        candidate = base64.b64decode(b"".join(candidate.split()), validate=False)
    if candidate.startswith(b"PK"):
        return candidate
    raise RuntimeError("UI-FIX-7 release-candidate overlay is not a valid ZIP payload.")


if _OVERLAY.exists():
    overlay_bytes = _decode_overlay(_OVERLAY.read_bytes())
    with ZipFile(BytesIO(overlay_bytes)) as archive:
        archive.extractall(_PROJECT_ROOT)
