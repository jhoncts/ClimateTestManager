"""Stage the exact user-approved UI-FIX-7 runtime before validation/build."""

from __future__ import annotations

import base64
import hashlib
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

_PROJECT_ROOT = Path(__file__).resolve().parent
_PARTS = [
    _PROJECT_ROOT / ".release-candidate" / f"ui7.part{index:02}.b64"
    for index in range(1, 9)
]
_EXPECTED_SHA256 = "4043f9762fef01a54c12eb4d8167aff8f7067fa0d46771c0f7bb1d2c88bb9e1a"
_EXPECTED_FILES = {
    "src/climatetest_manager/v084_stability.py",
    "src/climatetest_manager/domain/climate_rules.py",
    "src/climatetest_manager/ui/components/table17_interactive.py",
    "src/climatetest_manager/ui/views/final_new_test.py",
    "src/climatetest_manager/ui/views/agenda.py",
}


def _safe_member(name: str) -> None:
    relative = Path(name.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"Unsafe path in UI-FIX-7 staging payload: {name}")


def _stage_ui_fix7() -> None:
    if not all(part.exists() for part in _PARTS):
        return

    encoded = "".join(part.read_text(encoding="ascii") for part in _PARTS)
    payload = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != _EXPECTED_SHA256:
        raise RuntimeError(f"UI-FIX-7 staging payload checksum mismatch: {digest}")

    with ZipFile(BytesIO(payload)) as archive:
        names = archive.namelist()
        for name in names:
            _safe_member(name)
        files = {name for name in names if not name.endswith("/")}
        if files != _EXPECTED_FILES:
            raise RuntimeError("UI-FIX-7 staging payload contains an unexpected file set.")
        archive.extractall(_PROJECT_ROOT)


_stage_ui_fix7()
