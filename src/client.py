"""Atalho gráfico que abre o ClimateTest Manager servido na rede local."""

import argparse
import ctypes
import os
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

VERSION = "0.6.1"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--url", default="http://localhost:8550")
    return parser.parse_args()


def _server_available(server_url: str) -> bool:
    try:
        request = urllib.request.Request(server_url, method="GET")
        with urllib.request.urlopen(request, timeout=2) as response:
            return 200 <= response.status < 500
    except (OSError, urllib.error.URLError, ValueError):
        return False


def _wait_for_server(server_url: str, attempts: int = 30) -> bool:
    for _attempt in range(attempts):
        if _server_available(server_url):
            return True
        time.sleep(1)
    return False


def _diagnostics_directory() -> Path:
    program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    return Path(program_data) / "ClimateTestManager" / "Logs"


def _ask_retry(server_url: str) -> bool:
    message = (
        "O servidor central do ClimateTest Manager não respondeu.\n\n"
        f"Endereço verificado: {server_url}\n"
        "Código: CTM-CLI-001\n\n"
        "O programa não travou e seus dados não foram alterados. "
        "Clique em Repetir para testar novamente.\n\n"
        f"Diagnóstico: {_diagnostics_directory()}"
    )
    if os.name != "nt":
        print(message)
        return False

    retry_cancel = 0x00000005
    icon_warning = 0x00000030
    id_retry = 4
    result = ctypes.windll.user32.MessageBoxW(
        None,
        message,
        f"ClimateTest Manager v{VERSION} - Servidor indisponível",
        retry_cancel | icon_warning,
    )
    return result == id_retry


def main() -> None:
    server_url = _arguments().url.rstrip("/")
    while True:
        if _wait_for_server(server_url):
            webbrowser.open(server_url, new=2)
            return
        if not _ask_retry(server_url):
            return


if __name__ == "__main__":
    main()
