"""Ponto de entrada usado pelo Flet durante desenvolvimento e empacotamento."""

from pathlib import Path

import flet as ft

from climatetest_manager import round4_runtime, round6_compat, round6_email, round6_runtime
from climatetest_manager.client_session import enable_client_session_persistence

round4_runtime._App._refresh_shell_frame = round4_runtime._original_refresh_shell_frame
round6_runtime.install_round6_fixes()
round6_compat.install()
round6_email.install()

from climatetest_manager import round7_runtime, v084_stability  # noqa: E402
from climatetest_manager.round7_runtime import main  # noqa: E402

round7_runtime.install_round7_fixes()
v084_stability.install()

if __name__ == "__main__":
    enable_client_session_persistence()
    ft.run(main, assets_dir=str(Path(__file__).resolve().parent / "assets"))
