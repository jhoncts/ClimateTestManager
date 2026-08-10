"""Atalho gráfico que abre o ClimateTest Manager servido na rede local."""

import argparse
import time
import urllib.error
import urllib.request
import webbrowser


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--url", default="http://localhost:8550")
    return parser.parse_args()


def main() -> None:
    server_url = _arguments().url.rstrip("/")
    for _attempt in range(20):
        try:
            with urllib.request.urlopen(server_url, timeout=1):
                break
        except (OSError, urllib.error.URLError):
            time.sleep(1)
    webbrowser.open(server_url, new=2)


if __name__ == "__main__":
    main()
