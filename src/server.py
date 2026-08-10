"""Servidor web local do ClimateTest Manager para a rede privada do laboratório."""

import argparse
import os
from pathlib import Path

import flet as ft

from climatetest_manager.app import main


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Servidor LAN do ClimateTest Manager")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8550, type=int)
    parser.add_argument("--data-directory", default="")
    parser.add_argument("--backup-directory", default="")
    return parser.parse_args()


def run_server() -> None:
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
    ft.run(
        main,
        view=None,
        host=arguments.host,
        port=arguments.port,
        assets_dir=str(Path(__file__).resolve().parent / "assets"),
        no_cdn=True,
    )


if __name__ == "__main__":
    run_server()
