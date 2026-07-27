"""Testes dos caminhos locais configuráveis."""

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from climatetest_manager.config import (
    get_database_path,
    load_theme_mode,
    save_theme_mode,
)
from climatetest_manager.config import test_controls_enabled as controls_enabled


class DatabasePathTests(unittest.TestCase):
    def test_environment_override_keeps_database_outside_source(self) -> None:
        custom_directory = Path("temporary-test-data").resolve()

        with patch.dict(os.environ, {"CLIMATETEST_DATA_DIR": str(custom_directory)}):
            database_path = get_database_path()

        self.assertEqual(database_path, custom_directory / "climatetest_manager.db")

    def test_persists_theme_in_the_selected_data_directory(self) -> None:
        with (
            TemporaryDirectory() as temporary_directory,
            patch.dict(
                os.environ,
                {"CLIMATETEST_DATA_DIR": temporary_directory},
            ),
        ):
            self.assertEqual(load_theme_mode(), "light")
            save_theme_mode("dark")
            self.assertEqual(load_theme_mode(), "dark")

    def test_validation_control_requires_explicit_environment_flag(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(controls_enabled())
        with patch.dict(os.environ, {"CLIMATETEST_TEST_CONTROLS": "1"}):
            self.assertTrue(controls_enabled())


if __name__ == "__main__":
    unittest.main()
