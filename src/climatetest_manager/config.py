"""Caminhos e configurações locais da aplicação."""

import base64
import json
import os
import shutil
import sqlite3
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_path, user_data_path

APP_NAME = "ClimateTestManager"
APP_AUTHOR = "ClimateTestManager"
DATABASE_FILENAME = "climatetest_manager.db"
PREFERENCES_FILENAME = "preferences.json"
STORAGE_FILENAME = "storage.json"

_SYNCED_DIRECTORY_MARKERS = (
    "onedrive",
    "dropbox",
    "google drive",
    "google\u00a0drive",
    "icloud",
)


@dataclass(frozen=True, slots=True)
class StorageSettings:
    """Locais escolhidos para o banco ativo e a cópia externa."""

    data_directory: Path
    backup_directory: Path | None = None


@dataclass(frozen=True, slots=True)
class EmailSettings:
    """Configuração SMTP usada pelo notificador silencioso."""

    enabled: bool = False
    host: str = ""
    port: int = 587
    sender: str = ""
    username: str = ""
    password: str = ""
    use_tls: bool = True

    @property
    def is_configured(self) -> bool:
        return bool(
            self.enabled
            and self.host
            and self.sender
            and self.username
            and self.password
            and 1 <= self.port <= 65535
        )


def normalize_smtp_password(host: str, password: str) -> str:
    """Remove os separadores visuais usados nas senhas de app do Gmail."""

    if host.strip().casefold() == "smtp.gmail.com":
        return "".join(password.split())
    return password


def get_default_data_directory() -> Path:
    """Retorna o local padrão, sempre fora da pasta do código-fonte."""

    return user_data_path(APP_NAME, APP_AUTHOR, ensure_exists=False)


def get_storage_settings_path() -> Path:
    """Mantém a escolha de armazenamento fora do diretório que ela própria aponta."""

    custom_path = os.getenv("CLIMATETEST_STORAGE_CONFIG")
    if custom_path:
        return Path(custom_path).expanduser().resolve()
    return user_config_path(APP_NAME, APP_AUTHOR, ensure_exists=False) / STORAGE_FILENAME


def load_storage_settings() -> StorageSettings | None:
    """Carrega a escolha inicial sem impedir a recuperação de configuração inválida."""

    try:
        values = json.loads(get_storage_settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(values, dict):
        return None
    raw_data_directory = values.get("data_directory")
    if not isinstance(raw_data_directory, str) or not raw_data_directory.strip():
        return None
    raw_backup_directory = values.get("backup_directory")
    backup_directory = (
        Path(raw_backup_directory).expanduser().resolve()
        if isinstance(raw_backup_directory, str) and raw_backup_directory.strip()
        else None
    )
    return StorageSettings(
        data_directory=Path(raw_data_directory).expanduser().resolve(),
        backup_directory=backup_directory,
    )


def storage_setup_required() -> bool:
    """Solicita a escolha uma vez; a variável de ambiente continua sendo opção avançada."""

    if os.getenv("CLIMATETEST_DATA_DIR", "").strip():
        return False
    return load_storage_settings() is None


def get_data_directory() -> Path:
    """Retorna a pasta local escolhida para os dados do usuário."""

    custom_directory = os.getenv("CLIMATETEST_DATA_DIR")
    if custom_directory:
        return Path(custom_directory).expanduser().resolve()
    stored = load_storage_settings()
    return stored.data_directory if stored else get_default_data_directory()


def get_external_backup_directory() -> Path | None:
    """Retorna a pasta secundária, normalmente sincronizada pelo OneDrive."""

    custom_directory = os.getenv("CLIMATETEST_BACKUP_DIR")
    if custom_directory:
        return Path(custom_directory).expanduser().resolve()
    stored = load_storage_settings()
    return stored.backup_directory if stored else None


def suggest_onedrive_backup_directory() -> Path | None:
    """Sugere a pasta corporativa ou pessoal já configurada no Windows."""

    for variable in ("OneDriveCommercial", "OneDriveConsumer", "OneDrive"):
        value = os.getenv(variable, "").strip()
        if value:
            return Path(value).expanduser().resolve() / APP_NAME / "Backups"
    return None


def is_synced_directory(path: Path | str) -> bool:
    """Identifica locais cujo sincronizador pode disputar o arquivo SQLite aberto."""

    resolved = Path(path).expanduser().resolve()
    normalized = str(resolved).replace("\\", "/").casefold()
    if any(marker in normalized for marker in _SYNCED_DIRECTORY_MARKERS):
        return True
    for variable in ("OneDriveCommercial", "OneDriveConsumer", "OneDrive"):
        root = os.getenv(variable, "").strip()
        if root and resolved.is_relative_to(Path(root).expanduser().resolve()):
            return True
    return False


def _validate_storage_directory(path: Path, *, label: str) -> None:
    if path == Path(path.anchor):
        raise ValueError(f"Escolha uma pasta específica para {label}, não a raiz do disco.")
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".climatetest_write_test"
        probe.write_text("ok", encoding="ascii")
        probe.unlink()
    except OSError as error:
        raise ValueError(f"O sistema não consegue gravar na pasta de {label}.") from error


def _copy_existing_data(source: Path, destination: Path) -> None:
    """Copia banco e preferências sem apagar a origem, permitindo retorno seguro."""

    source_database = source / DATABASE_FILENAME
    destination_database = destination / DATABASE_FILENAME
    if not source_database.exists() or source.resolve() == destination.resolve():
        return
    if destination_database.exists():
        raise ValueError(
            "A pasta escolhida já contém um banco de dados. Escolha uma pasta vazia para "
            "evitar a substituição de informações."
        )
    source_connection: sqlite3.Connection | None = None
    destination_connection: sqlite3.Connection | None = None
    try:
        source_connection = sqlite3.connect(source_database)
        destination_connection = sqlite3.connect(destination_database)
        source_connection.backup(destination_connection)
    except sqlite3.Error as error:
        if destination_connection is not None:
            with suppress(sqlite3.Error):
                destination_connection.close()
            destination_connection = None
        with suppress(OSError):
            destination_database.unlink(missing_ok=True)
        raise ValueError("Não foi possível copiar com segurança o banco existente.") from error
    finally:
        if destination_connection is not None:
            with suppress(sqlite3.Error):
                destination_connection.close()
        if source_connection is not None:
            with suppress(sqlite3.Error):
                source_connection.close()
    source_preferences = source / PREFERENCES_FILENAME
    if source_preferences.exists():
        shutil.copy2(source_preferences, destination / PREFERENCES_FILENAME)


def save_storage_settings(
    data_directory: Path | str,
    backup_directory: Path | str | None,
) -> StorageSettings:
    """Valida, preserva dados existentes e persiste a decisão do responsável."""

    data_path = Path(data_directory).expanduser().resolve()
    backup_path = (
        Path(backup_directory).expanduser().resolve()
        if backup_directory is not None and str(backup_directory).strip()
        else None
    )
    if is_synced_directory(data_path):
        raise ValueError(
            "O banco ativo não pode ficar no OneDrive ou em outra pasta sincronizada. "
            "Escolha uma pasta local e use o OneDrive para as cópias de segurança."
        )
    if str(data_path).startswith(("//", "\\\\")):
        raise ValueError(
            "O banco ativo não pode ficar em uma pasta de rede. Escolha uma pasta local."
        )
    if backup_path is not None and backup_path == data_path:
        raise ValueError("A cópia de segurança deve ficar em uma pasta diferente dos dados.")
    _validate_storage_directory(data_path, label="os dados")
    if backup_path is not None:
        _validate_storage_directory(backup_path, label="as cópias de segurança")

    current_path = get_data_directory()
    _copy_existing_data(current_path, data_path)
    values = {
        "data_directory": str(data_path),
        "backup_directory": str(backup_path) if backup_path else "",
    }
    settings_path = get_storage_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = settings_path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(values, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(settings_path)
    return StorageSettings(data_path, backup_path)


def get_database_path() -> Path:
    """Retorna o caminho do arquivo SQLite de produção."""

    return get_data_directory() / DATABASE_FILENAME


def get_exports_directory() -> Path:
    """Retorna a pasta local usada para relatórios CSV e arquivos de agenda."""

    return get_data_directory() / "exports"


def load_theme_mode() -> str:
    """Carrega a preferência visual sem impedir a abertura por arquivo inválido."""

    values = load_preferences()
    return "dark" if values.get("theme_mode") == "dark" else "light"


def save_theme_mode(mode: str) -> None:
    """Persiste o tema sem apagar as demais preferências locais."""

    normalized = "dark" if mode == "dark" else "light"
    save_preference("theme_mode", normalized)


def load_preferences() -> dict[str, object]:
    """Carrega preferências locais e tolera arquivo ausente ou inválido."""

    preferences_path = get_data_directory() / PREFERENCES_FILENAME
    try:
        values = json.loads(preferences_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return values if isinstance(values, dict) else {}


def save_preference(key: str, value: object | None) -> None:
    """Atualiza uma preferência sem descartar as outras chaves."""

    values = load_preferences()
    if value is None:
        values.pop(key, None)
    else:
        values[key] = value
    preferences_path = get_data_directory() / PREFERENCES_FILENAME
    preferences_path.parent.mkdir(parents=True, exist_ok=True)
    preferences_path.write_text(
        json.dumps(values, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _protect_windows_secret(value: str) -> str:
    """Protege um segredo com DPAPI no servidor Windows, sem gravar texto aberto."""

    if sys.platform != "win32":
        raise OSError("O armazenamento protegido de senha está disponível somente no Windows.")
    import ctypes
    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD),
            ("data", ctypes.POINTER(ctypes.c_ubyte)),
        ]

    raw = value.encode("utf-8")
    buffer = ctypes.create_string_buffer(raw)
    input_blob = DataBlob(
        len(raw),
        ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    output_blob = DataBlob()
    protected = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        "ClimateTest Manager SMTP",
        None,
        None,
        None,
        0x5,  # CRYPTPROTECT_UI_FORBIDDEN | CRYPTPROTECT_LOCAL_MACHINE
        ctypes.byref(output_blob),
    )
    if not protected:
        raise OSError("O Windows não conseguiu proteger a senha de e-mail.")
    try:
        encrypted = ctypes.string_at(output_blob.data, output_blob.size)
    finally:
        ctypes.windll.kernel32.LocalFree(output_blob.data)
    return base64.b64encode(encrypted).decode("ascii")


def _unprotect_windows_secret(value: str) -> str:
    if sys.platform != "win32" or not value:
        return ""
    import ctypes
    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD),
            ("data", ctypes.POINTER(ctypes.c_ubyte)),
        ]

    try:
        encrypted = base64.b64decode(value, validate=True)
    except ValueError:
        return ""
    buffer = ctypes.create_string_buffer(encrypted)
    input_blob = DataBlob(
        len(encrypted),
        ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    output_blob = DataBlob()
    unprotected = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        0x1,
        ctypes.byref(output_blob),
    )
    if not unprotected:
        return ""
    try:
        plain = ctypes.string_at(output_blob.data, output_blob.size)
    finally:
        ctypes.windll.kernel32.LocalFree(output_blob.data)
    return plain.decode("utf-8")


def load_email_settings() -> EmailSettings:
    """Carrega o SMTP, priorizando a senha protegida configurada pela interface."""

    values = load_preferences()
    host = str(values.get("smtp_host", "")).strip()
    protected = values.get("smtp_password_protected")
    password = _unprotect_windows_secret(protected) if isinstance(protected, str) else ""
    if not password:
        password = os.getenv("CLIMATETEST_SMTP_PASSWORD", "")
    password = normalize_smtp_password(host, password)
    raw_port = values.get("smtp_port", 587)
    try:
        port = int(raw_port)
    except (TypeError, ValueError):
        port = 587
    return EmailSettings(
        enabled=values.get("smtp_enabled") is True,
        host=host,
        port=port,
        sender=str(values.get("smtp_sender", "")).strip(),
        username=str(values.get("smtp_username", "")).strip(),
        password=password,
        use_tls=values.get("smtp_use_tls") is not False,
    )


def save_email_settings(
    settings: EmailSettings,
    *,
    new_password: str = "",
) -> None:
    """Persiste o SMTP e protege uma nova senha para os processos do servidor."""

    values = load_preferences()
    values.update(
        {
            "smtp_enabled": settings.enabled,
            "smtp_host": settings.host.strip(),
            "smtp_port": settings.port,
            "smtp_sender": settings.sender.strip(),
            "smtp_username": settings.username.strip(),
            "smtp_use_tls": settings.use_tls,
        }
    )
    if new_password:
        normalized_password = normalize_smtp_password(settings.host, new_password)
        if not normalized_password:
            raise ValueError("A senha SMTP não pode conter somente espaços.")
        values["smtp_password_protected"] = _protect_windows_secret(normalized_password)
    preferences_path = get_data_directory() / PREFERENCES_FILENAME
    preferences_path.parent.mkdir(parents=True, exist_ok=True)
    preferences_path.write_text(
        json.dumps(values, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_remembered_session_token() -> str | None:
    """Lê o token opaco usado somente quando o usuário escolheu permanecer conectado."""

    value = load_preferences().get("remembered_session_token")
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def save_remembered_session_token(token: str | None) -> None:
    """Salva ou remove a sessão persistente deste computador."""

    save_preference("remembered_session_token", token)


def test_controls_enabled() -> bool:
    """Mantém o botão de avanço fora do uso normal e do executável de produção."""

    return os.getenv("CLIMATETEST_TEST_CONTROLS", "").strip() == "1"
