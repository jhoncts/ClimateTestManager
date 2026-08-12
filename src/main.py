"""Ponto de entrada usado pelo Flet durante desenvolvimento e empacotamento."""

from pathlib import Path

import flet as ft

from climatetest_manager import round4_runtime
from climatetest_manager.client_session import enable_client_session_persistence
from climatetest_manager.round4_runtime import main

round4_runtime._App._refresh_shell_frame = round4_runtime._original_refresh_shell_frame

if __name__ == "__main__":
    enable_client_session_persistence()
    ft.run(main, assets_dir=str(Path(__file__).resolve().parent / "assets"))
