"""Caminhos e configurações locais da aplicação."""

import json
import os
from pathlib import Path

from platformdirs import user_data_path

APP_NAME = "ClimateTestManager"
APP_AUTHOR = "ClimateTestManager"
DATABASE_FILENAME = "climatetest_manager.db"
PREFERENCES_FILENAME = "preferences.json"


def get_data_directory() -> Path:
    """Retorna uma pasta gravável e estável para os dados do usuário."""

    custom_directory = os.getenv("CLIMATETEST_DATA_DIR")
    if custom_directory:
        return Path(custom_directory).expanduser().resolve()
    return user_data_path(APP_NAME, APP_AUTHOR, ensure_exists=False)


def get_database_path() -> Path:
    """Retorna o caminho do arquivo SQLite de produção."""

    return get_data_directory() / DATABASE_FILENAME


def get_exports_directory() -> Path:
    """Retorna a pasta local usada para relatórios CSV e arquivos de agenda."""

    return get_data_directory() / "exports"


def load_theme_mode() -> str:
    """Carrega a preferência visual sem impedir a abertura por arquivo inválido."""

    preferences_path = get_data_directory() / PREFERENCES_FILENAME
    try:
        values = json.loads(preferences_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return "light"
    return "dark" if values.get("theme_mode") == "dark" else "light"


def save_theme_mode(mode: str) -> None:
    """Persiste apenas a preferência local de tema."""

    normalized = "dark" if mode == "dark" else "light"
    preferences_path = get_data_directory() / PREFERENCES_FILENAME
    preferences_path.parent.mkdir(parents=True, exist_ok=True)
    preferences_path.write_text(
        json.dumps({"theme_mode": normalized}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_controls_enabled() -> bool:
    """Mantém o botão de avanço fora do uso normal e do executável de produção."""

    return os.getenv("CLIMATETEST_TEST_CONTROLS", "").strip() == "1"
