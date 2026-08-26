from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from climatetest_manager.product_identity import desktop_activation_port
from climatetest_manager.services.update_manifest import create_manifest
from climatetest_manager.services.updates import (
    central_update_checks_enabled,
    installed_role_and_server,
    parse_update_manifest,
    update_check_interval_seconds,
)


def _manifest() -> dict[str, object]:
    return {
        "schema": 1,
        "product": "ClimateTestManager",
        "channel": "stable",
        "version": "0.8.6",
        "build_revision": "R11-20260825",
        "published_at": "2026-08-25T12:00:00Z",
        "mandatory": False,
        "release_url": "https://github.com/jhoncts/ClimateTestManager/releases/tag/v0.8.6",
        "release_notes": "Atualização global.",
        "installer": {
            "name": "ClimateTestManager-Setup-v0.8.6.exe",
            "url": (
                "https://github.com/jhoncts/ClimateTestManager/releases/download/"
                "v0.8.6/ClimateTestManager-Setup-v0.8.6.exe"
            ),
            "size": 224_000_000,
            "sha256": "a" * 64,
        },
    }


def test_manifest_exposes_rollout_build_and_verified_installer() -> None:
    update = parse_update_manifest(_manifest(), current_version="0.8.5")

    assert update is not None
    assert update.version == "0.8.6"
    assert update.build_revision == "R11-20260825"
    assert update.expected_size == 224_000_000
    assert update.expected_sha256 == "a" * 64
    assert update.source == "manifest"


def test_manifest_rejects_foreign_product_and_download_host() -> None:
    foreign_product = _manifest()
    foreign_product["product"] = "CalibraLab"
    with pytest.raises(ValueError, match="outro produto"):
        parse_update_manifest(foreign_product, current_version="0.8.5")

    foreign_host = _manifest()
    installer = foreign_host["installer"]
    assert isinstance(installer, dict)
    installer["url"] = "https://example.invalid/update.exe"
    with pytest.raises(ValueError, match="canal oficial"):
        parse_update_manifest(foreign_host, current_version="0.8.5")


def test_manifest_generator_uses_real_size_and_hash() -> None:
    with TemporaryDirectory() as temporary_directory:
        installer = Path(temporary_directory) / "ClimateTestManager-Setup-v0.8.6.exe"
        installer.write_bytes(b"verified-installer")

        manifest = create_manifest(
            version="0.8.6",
            build_revision="R11-20260825",
            installer=installer,
            repository="jhoncts/ClimateTestManager",
            tag="v0.8.6",
            published_at="2026-08-25T12:00:00Z",
        )

    installer_data = manifest["installer"]
    assert isinstance(installer_data, dict)
    assert installer_data["size"] == len(b"verified-installer")
    assert installer_data["sha256"] == (
        "f3a5a3449d7bebc6b1b0b2b30509b0f634bfe1104c2db73a944a428e916a4f25"
    )


def test_local_role_is_namespaced_to_climatetest_programdata() -> None:
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory) / "ClimateTestManager"
        root.mkdir()
        (root / "client-mode.marker").write_text("client", encoding="ascii")
        (root / "server.url").write_text("http://lab-server:8550", encoding="utf-8")
        with patch.dict("os.environ", {"PROGRAMDATA": temporary_directory}, clear=False):
            assert installed_role_and_server() == ("client", "http://lab-server:8550")


def test_update_interval_is_bounded() -> None:
    with patch.dict("os.environ", {"CLIMATETEST_UPDATE_INTERVAL_SECONDS": "10"}):
        assert update_check_interval_seconds() == 900
    with patch.dict("os.environ", {"CLIMATETEST_UPDATE_INTERVAL_SECONDS": "999999"}):
        assert update_check_interval_seconds() == 86400


def test_only_central_server_monitors_public_updates() -> None:
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory) / "ClimateTestManager"
        root.mkdir()
        with patch.dict("os.environ", {"PROGRAMDATA": temporary_directory}, clear=False):
            (root / "client-mode.marker").write_text("client", encoding="ascii")
            assert central_update_checks_enabled() is False

            (root / "client-mode.marker").unlink()
            (root / "server-mode.marker").write_text("server", encoding="ascii")
            assert central_update_checks_enabled() is True

            with patch.dict("os.environ", {"CLIMATETEST_DISABLE_UPDATE_CHECK": "1"}):
                assert central_update_checks_enabled() is False


def test_each_product_id_derives_a_different_activation_port() -> None:
    assert desktop_activation_port("com.jhoncts.climatetestmanager") != desktop_activation_port(
        "com.jhoncts.calibralab"
    )
