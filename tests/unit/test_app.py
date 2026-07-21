"""Teste de montagem da janela principal sem abrir uma janela real."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import flet as ft

from climatetest_manager.app import main


class FakePage:
    """Implementação mínima das operações usadas pelo controlador da aplicação."""

    def __init__(self) -> None:
        self.window = SimpleNamespace()
        self.controls: list[ft.Control] = []
        self.update_count = 0

    def add(self, *controls: ft.Control) -> None:
        self.controls.extend(controls)

    def clean(self) -> None:
        self.controls.clear()

    def update(self) -> None:
        self.update_count += 1


class ApplicationTests(unittest.TestCase):
    def test_main_builds_dashboard_and_database(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            page = FakePage()
            with patch.dict("os.environ", {"CLIMATETEST_DATA_DIR": temporary_directory}):
                main(page)  # type: ignore[arg-type]

            self.assertEqual(len(page.controls), 1)
            self.assertIsInstance(page.controls[0], ft.Row)
            self.assertGreaterEqual(page.update_count, 1)
            self.assertTrue(Path(temporary_directory, "climatetest_manager.db").exists())


if __name__ == "__main__":
    unittest.main()
