"""Servidor local do ClimateTest Manager para a rede privada do laboratório."""

import argparse
import os
import sys
from pathlib import Path

import flet as ft

from climatetest_manager.client_session import enable_client_session_persistence
from climatetest_manager.production_app import main
from climatetest_manager.services.network import DiscoveryResponder


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Servidor LAN do ClimateTest Manager")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8550, type=int)
    parser.add_argument("--data-directory", default="")
    parser.add_argument("--backup-directory", default="")
    return parser.parse_args()


def _ensure_standard_streams() -> None:
    """Garante streams válidos quando o executável foi empacotado com --noconsole.

    No Windows, o PyInstaller pode definir sys.stdout/sys.stderr como None em executáveis
    sem console. O Uvicorn consulta ``isatty()`` nesses streams durante a configuração do
    logging; sem esta proteção o servidor encerra antes mesmo de abrir a porta HTTP.
    """

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
