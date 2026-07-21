"""Testes dos caminhos locais configuráveis."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from climatetest_manager.config import get_database_path


class DatabasePathTests(unittest.TestCase):
    def test_environment_override_keeps_database_outside_source(self) -> None:
        custom_directory = Path("temporary-test-data").resolve()

        with patch.dict(os.environ, {"CLIMATETEST_DATA_DIR": str(custom_directory)}):
            database_path = get_database_path()

        self.assertEqual(database_path, custom_directory / "climatetest_manager.db")


if __name__ == "__main__":
    unittest.main()
