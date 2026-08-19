"""Servidor local do ClimateTest Manager para a rede privada do laboratório."""

import argparse
import os
import sys
from pathlib import Path

import flet as ft

from climatetest_manager import round4_runtime, round6_compat, round6_email, round6_runtime
from climatetest_manager.client_session import enable_client_session_persistence
from climatetest_manager.services.network import DiscoveryResponder

round4_runtime._App._refresh_shell_frame = round4_runtime._original_refresh_shell_frame
round6_runtime.install_round6_fixes()
round6_compat.install()
round6_email.install()

from climatetest_manager import (  # noqa: E402
    round7_runtime,
    v084_stability,
    v086_conditioning,
    v086_navigation,
    v086_runtime,
    v086_skip_policy,
    v086_sync,
    v086_tracking,
)
from climatetest_manager.round7_runtime import main  # noqa: E402

round7_runtime.install_round7_fixes()
v084_stability.install()
v086_runtime.install()
v086_conditioning.install()
v086_skip_policy.install()
v086_tracking.install()
v086_sync.install()
v086_navigation.install()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Servidor LAN do ClimateTest Manager")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8550, type=int)
    parser.add_argument("--data-directory", default="")
    parser.add_argument("--backup-directory", default="")
    return parser.parse_args()


def _ensure_standard_streams() -> None:
    if sys.stdin is None:
        sys.stdin = open(os.devnull, encoding="utf-8")  # noqa: SIM115
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115


def run_server() -> None:
    _ensure_standard_streams()
    enable_client_session_persistence()
    arguments = _arguments()
    if arguments.data_directory:
        os.environ["CLIMATETEST_DATA_DIR"] = arguments.data_directory
        os.environ.setdefault(
            "CLIMATETEST_STORAGE_CONFIG",
            str(Path(arguments.data_directory) / "storage.json"),
        )
    if arguments.backup_directory:
        os.environ["CLIMATETEST_BACKUP_DIR"] = arguments.backup_directory
    os.environ["CLIMATETEST_SERVER_MODE"] = "1"
    os.environ["FLET_FORCE_WEB_SERVER"] = "true"
    os.environ["FLET_SERVER_IP"] = arguments.host
    os.environ["FLET_SERVER_PORT"] = str(arguments.port)
    discovery = DiscoveryResponder(app_port=arguments.port)
    discovery.start()
    try:
        ft.run(
            main,
            view=None,
            host=arguments.host,
            port=arguments.port,
            assets_dir=str(Path(__file__).resolve().parent / "assets"),
            no_cdn=True,
        )
    finally:
        discovery.stop()


if __name__ == "__main__":
    run_server()
