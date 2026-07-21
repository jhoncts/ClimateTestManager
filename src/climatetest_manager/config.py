"""Caminhos e configurações locais da aplicação."""

import os
from pathlib import Path

from platformdirs import user_data_path

APP_NAME = "ClimateTestManager"
APP_AUTHOR = "ClimateTestManager"
DATABASE_FILENAME = "climatetest_manager.db"


def get_data_directory() -> Path:
    """Retorna uma pasta gravável e estável para os dados do usuário."""

    custom_directory = os.getenv("CLIMATETEST_DATA_DIR")
    if custom_directory:
        return Path(custom_directory).expanduser().resolve()
    return user_data_path(APP_NAME, APP_AUTHOR, ensure_exists=False)


def get_database_path() -> Path:
    """Retorna o caminho do arquivo SQLite de produção."""

    return get_data_directory() / DATABASE_FILENAME
