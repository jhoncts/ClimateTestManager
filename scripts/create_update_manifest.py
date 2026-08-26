"""Gera o manifesto estável publicado junto com cada instalador Windows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from climatetest_manager.services.update_manifest import create_manifest


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--build-revision", required=True)
    parser.add_argument("--installer", required=True, type=Path)
    parser.add_argument("--repository", default="jhoncts/ClimateTestManager")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--notes-file", type=Path)
    parser.add_argument("--mandatory", action="store_true")
    parser.add_argument("--signer-subject", default="")
    parser.add_argument("--signer-thumbprint", default="")
    parser.add_argument("--published-at", default="")
    return parser.parse_args()


def main() -> None:
    arguments = _arguments()
    notes = ""
    if arguments.notes_file is not None:
        notes = arguments.notes_file.read_text(encoding="utf-8")
    manifest = create_manifest(
        version=arguments.version,
        build_revision=arguments.build_revision,
        installer=arguments.installer,
        repository=arguments.repository,
        tag=arguments.tag,
        release_notes=notes,
        mandatory=arguments.mandatory,
        signer_subject=arguments.signer_subject,
        signer_thumbprint=arguments.signer_thumbprint,
        published_at=arguments.published_at,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(arguments.output)


if __name__ == "__main__":
    main()
