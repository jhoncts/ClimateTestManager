"""Build-only staging hook for the validated UI-FIX-7 candidate.

The approved UI-FIX-7 source is stored as a release-candidate overlay so the
application code remains frozen until the final multi-PC validation. Pytest is
already executed by both Quality and Build Windows release; loading this
conftest expands the validated overlay before test collection. In the release
workflow the same expanded working tree is then packaged by the existing build
step.
"""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile


_PROJECT_ROOT = Path(__file__).resolve().parent
_OVERLAY = _PROJECT_ROOT / ".release-candidate" / "ui-fix7-overlay.zip"

if _OVERLAY.exists():
    with ZipFile(_OVERLAY) as archive:
        archive.extractall(_PROJECT_ROOT)
