"""Testes dos caminhos locais configuráveis."""

import os
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from climatetest_manager.config import (
    EmailSettings,
    get_database_path,
    get_external_backup_directory,
    load_email_settings,
    load_remembered_session_token,
    load_storage_settings,
    load_theme_mode,
    normalize_smtp_password,
    save_email_settings,
    save_remembered_session_token,
    save_storage_settings,
    save_theme_mode,
    storage_setup_required,
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

    def test_theme_and_remembered_session_do_not_overwrite_each_other(self) -> None:
        with (
            TemporaryDirectory() as temporary_directory,
            patch.dict(
                os.environ,
                {"CLIMATETEST_DATA_DIR": temporary_directory},
            ),
        ):
            save_remembered_session_token("opaque-token")
            save_theme_mode("dark")
            self.assertEqual(load_theme_mode(), "dark")
            self.assertEqual(load_remembered_session_token(), "opaque-token")
            save_remembered_session_token(None)
            self.assertIsNone(load_remembered_session_token())

    def test_validation_control_requires_explicit_environment_flag(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(controls_enabled())
        with patch.dict(os.environ, {"CLIMATETEST_TEST_CONTROLS": "1"}):
            self.assertTrue(controls_enabled())

    def test_email_preferences_keep_secret_out_of_plain_text(self) -> None:
        with (
            TemporaryDirectory() as temporary_directory,
            patch.dict(
                os.environ,
                {
                    "CLIMATETEST_DATA_DIR": temporary_directory,
                    "CLIMATETEST_SMTP_PASSWORD": "SenhaSMTP123",
                },
            ),
            patch(
                "climatetest_manager.config._protect_windows_secret",
                return_value="segredo-protegido",
            ),
        ):
            save_email_settings(
                EmailSettings(
                    enabled=True,
                    host="smtp.example.com",
                    port=587,
                    sender="laboratorio@example.com",
                    username="laboratorio@example.com",
                    use_tls=True,
                ),
                new_password="SenhaSMTP123",
            )
            loaded = load_email_settings()
            preferences = Path(temporary_directory, "preferences.json").read_text(encoding="utf-8")

        self.assertTrue(loaded.is_configured)
        self.assertEqual(loaded.password, "SenhaSMTP123")
        self.assertNotIn("SenhaSMTP123", preferences)

    def test_gmail_password_removes_visual_spaces(self) -> None:
        self.assertEqual(
            normalize_smtp_password("smtp.gmail.com", "abcd efgh\tijkl\nmnop"),
            "abcdefghijklmnop",
        )
        self.assertEqual(
            normalize_smtp_password("smtp.example.com", "senha com espaços"),
            "senha com espaços",
        )

    def test_saved_secret_has_priority_over_stale_environment_password(self) -> None:
        with (
            TemporaryDirectory() as temporary_directory,
            patch.dict(
                os.environ,
                {
                    "CLIMATETEST_DATA_DIR": temporary_directory,
                    "CLIMATETEST_SMTP_PASSWORD": "senha-com-ó-antiga",
                },
            ),
            patch(
                "climatetest_manager.config._protect_windows_secret",
                return_value="segredo-protegido",
            ),
            patch(
                "climatetest_manager.config._unprotect_windows_secret",
                return_value="abcd efgh ijkl mnop",
            ),
        ):
            save_email_settings(
                EmailSettings(
                    enabled=True,
                    host="smtp.gmail.com",
                    port=587,
                    sender="climatetest.sender@gmail.com",
                    username="climatetest.sender@gmail.com",
                ),
                new_password="abcd efgh ijkl mnop",
            )
            loaded = load_email_settings()

        self.assertEqual(loaded.password, "abcdefghijklmnop")

    def test_storage_setup_persists_local_database_and_onedrive_backup(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            default_directory = root / "default"
            settings_path = root / "config" / "storage.json"
            data_directory = root / "dados"
            backup_directory = root / "OneDrive - Laboratorio" / "Backups"
            with (
                patch.dict(os.environ, {}, clear=True),
                patch(
                    "climatetest_manager.config.get_default_data_directory",
                    return_value=default_directory,
                ),
                patch(
                    "climatetest_manager.config.get_storage_settings_path",
                    return_value=settings_path,
                ),
            ):
                self.assertTrue(storage_setup_required())
                saved = save_storage_settings(data_directory, backup_directory)

                self.assertFalse(storage_setup_required())
                self.assertEqual(get_database_path(), data_directory / "climatetest_manager.db")
                self.assertEqual(get_external_backup_directory(), backup_directory)
                self.assertEqual(load_storage_settings(), saved)

    def test_storage_setup_rejects_active_database_in_onedrive(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with (
                patch.dict(
                    os.environ,
                    {"OneDriveCommercial": str(root / "NuvemCorporativa")},
                    clear=True,
                ),
                patch(
                    "climatetest_manager.config.get_default_data_directory",
                    return_value=root / "default",
                ),
                patch(
                    "climatetest_manager.config.get_storage_settings_path",
                    return_value=root / "config" / "storage.json",
                ),
                self.assertRaisesRegex(ValueError, "não pode ficar no OneDrive"),
            ):
                save_storage_settings(
                    root / "NuvemCorporativa" / "dados",
                    root / "backup",
                )

    def test_storage_setup_copies_existing_database_without_deleting_source(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "origem"
            destination = root / "destino"
            source.mkdir()
            source_database = source / "climatetest_manager.db"
            connection = sqlite3.connect(source_database)
            connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
            connection.execute("INSERT INTO sample VALUES ('preservado')")
            connection.commit()
            connection.close()
            (source / "preferences.json").write_text(
                '{"theme_mode": "dark"}',
                encoding="utf-8",
            )

            with (
                patch.dict(os.environ, {}, clear=True),
                patch(
                    "climatetest_manager.config.get_default_data_directory",
                    return_value=source,
                ),
                patch(
                    "climatetest_manager.config.get_storage_settings_path",
                    return_value=root / "config" / "storage.json",
                ),
            ):
                save_storage_settings(destination, root / "OneDrive" / "Backups")

            copied = sqlite3.connect(destination / "climatetest_manager.db")
            try:
                value = copied.execute("SELECT value FROM sample").fetchone()[0]
            finally:
                copied.close()
            self.assertEqual(value, "preservado")
            self.assertTrue(source_database.exists())
            self.assertTrue((destination / "preferences.json").exists())


if __name__ == "__main__":
    unittest.main()
