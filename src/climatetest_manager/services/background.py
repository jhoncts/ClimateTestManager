"""Instalação explícita do agente local de notificações no Windows."""

import os
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

from climatetest_manager.config import get_data_directory, is_synced_directory

TASK_NAME = "ClimateTestManager-Notifications"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _notification_action(data_directory: str = "") -> str:
    """Resolve um executável silencioso tanto no pacote quanto no desenvolvimento."""

    candidates: list[tuple[Path, Path | None]] = []
    if getattr(sys, "frozen", False):
        candidates.append(
            (Path(sys.executable).resolve().with_name("ClimateTestNotifier.exe"), None)
        )
    project_root = _project_root()
    candidates.extend(
        [
            (
                project_root / "dist" / "ClimateTestManager-v0.6.0" / "ClimateTestNotifier.exe",
                None,
            ),
            (project_root / "dist" / "ClimateTestNotifier.exe", None),
            (
                project_root / ".venv" / "Scripts" / "pythonw.exe",
                project_root / "src" / "notifier.py",
            ),
        ]
    )
    for executable, entrypoint in candidates:
        if not executable.exists() or (entrypoint is not None and not entrypoint.exists()):
            continue
        parts = [f'"{executable}"']
        if entrypoint is not None:
            parts.append(f'"{entrypoint}"')
        if data_directory:
            parts.extend(["--data-directory", f'"{data_directory}"'])
        return " ".join(parts)
    raise RuntimeError(
        "O notificador silencioso não foi encontrado. Gere ou reinstale os executáveis."
    )


def notification_task_installed() -> bool:
    """Confirma que a tarefa existe e está habilitada no Windows."""

    if sys.platform != "win32":
        return False
    result = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", TASK_NAME, "/XML"],
        capture_output=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        return False
    task_xml_output = result.stdout
    if isinstance(task_xml_output, bytes) and not task_xml_output.startswith(
        (b"\xff\xfe", b"\xfe\xff", b"<\x00", b"\x00<")
    ):
        task_xml_output = task_xml_output.decode(errors="replace")
    try:
        task_xml = ElementTree.fromstring(task_xml_output)
    except (ElementTree.ParseError, TypeError):
        return False
    enabled = task_xml.find(".//{*}Enabled")
    if enabled is None:
        return True
    return (enabled.text or "").strip().casefold() == "true"


def configure_notification_task(*, enable: bool) -> None:
    """Cria ou remove diretamente a tarefa após uma ação consciente do usuário."""

    if sys.platform != "win32":
        raise RuntimeError("Os avisos em segundo plano estão disponíveis somente no Windows.")
    data_directory = os.getenv("CLIMATETEST_DATA_DIR", "").strip()
    if enable and is_synced_directory(get_data_directory()):
        raise RuntimeError(
            "O banco SQLite ativo não deve ficar no OneDrive. "
            "Use o OneDrive somente para as cópias de segurança."
        )
    if enable:
        command = [
            "schtasks.exe",
            "/Create",
            "/TN",
            TASK_NAME,
            "/SC",
            "MINUTE",
            "/MO",
            "5",
            "/TR",
            _notification_action(data_directory),
            "/IT",
            "/F",
        ]
    else:
        command = ["schtasks.exe", "/Delete", "/TN", TASK_NAME, "/F"]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Falha desconhecida."
        raise RuntimeError(message)
