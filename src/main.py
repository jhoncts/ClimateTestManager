"""Ponto de entrada usado pelo Flet durante desenvolvimento e empacotamento."""

from pathlib import Path

import flet as ft

from climatetest_manager.app import main
from climatetest_manager.client_session import enable_client_session_persistence

if __name__ == "__main__":
    enable_client_session_persistence()
    ft.run(main, assets_dir=str(Path(__file__).resolve().parent / "assets"))
