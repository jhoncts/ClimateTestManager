"""Build-only staging hook for the validated UI-FIX-7 candidate.

The exact UI-FIX-7 runtime delta is stored as a small, valid ZIP generated from
the user-approved source. Pytest expands it before test collection; the Windows
release workflow then packages that same expanded working tree.
"""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

_PROJECT_ROOT = Path(__file__).resolve().parent
_OVERLAY = _PROJECT_ROOT / ".release-candidate" / "ui-fix7-overlay.zip"

if _OVERLAY.exists():
    with ZipFile(_OVERLAY) as archive:
        archive.extractall(_PROJECT_ROOT)
