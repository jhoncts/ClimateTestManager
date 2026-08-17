"""Stage the exact user-approved UI-FIX-7 runtime before validation/build."""

from __future__ import annotations

import base64
import hashlib
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

_PROJECT_ROOT = Path(__file__).resolve().parent
_PARTS = [_PROJECT_ROOT / ".release-candidate" / f"ui7.part{index:02}.b64" for index in range(1, 9)]
_EXPECTED_FILE_SHA256 = {
    "src/climatetest_manager/v084_stability.py": "2d3ee3371e4d7cd547b1b5844649d9ffb61b44c60505744cd434c5991fe43dc5",
    "src/climatetest_manager/domain/climate_rules.py": "e5976ca14bb7859d72b6707633c88431697ae8366eb53598670e149a82d75a0c",
    "src/climatetest_manager/ui/components/table17_interactive.py": "699971177e3673ea531f912c5c936314a1343cb51909011a96392490ff84369e",
    "src/climatetest_manager/ui/views/final_new_test.py": "a0845d7d72760650e8b6005dc914a56ae1215778d0d83fc49e0536e86d457f30",
    "src/climatetest_manager/ui/views/agenda.py": "fa3e66e721a2cadb43532b01ac38da85efacb70cfbd7909100e1260084d04b65",
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

    with ZipFile(BytesIO(payload)) as archive:
        names = archive.namelist()
        for name in names:
            _safe_member(name)
        files = {name for name in names if not name.endswith("/")}
        if files != set(_EXPECTED_FILE_SHA256):
            raise RuntimeError("UI-FIX-7 staging payload contains an unexpected file set.")

        for name, expected_digest in _EXPECTED_FILE_SHA256.items():
            digest = hashlib.sha256(archive.read(name)).hexdigest()
            if digest != expected_digest:
                raise RuntimeError(
                    f"UI-FIX-7 staging file checksum mismatch for {name}: {digest}"
                )

        archive.extractall(_PROJECT_ROOT)


_stage_ui_fix7()
