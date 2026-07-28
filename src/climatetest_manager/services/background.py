"""Instalação explícita do agente local de notificações no Windows."""

import os
import subprocess
import sys
from pathlib import Path

TASK_NAME = "ClimateTestManager-Notifications"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def notification_task_installed() -> bool:
    """Consulta a tarefa sem modificar o Windows."""

    if sys.platform != "win32":
        return False
    result = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", TASK_NAME],
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return result.returncode == 0


def configure_notification_task(*, enable: bool) -> None:
    """Executa o script de instalação ou remoção após uma ação consciente do usuário."""

    if sys.platform != "win32":
        raise RuntimeError("Os avisos em segundo plano estão disponíveis somente no Windows.")
    script_name = "install_notifier_task.ps1" if enable else "uninstall_notifier_task.ps1"
    script = _project_root() / "scripts" / script_name
    if not script.exists():
        raise RuntimeError(
            "O script do agente não foi encontrado. Reinstale o ClimateTest Manager."
        )
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]
    data_directory = os.getenv("CLIMATETEST_DATA_DIR", "").strip()
    if enable and data_directory:
        command.extend(["-DataDirectory", data_directory])
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
