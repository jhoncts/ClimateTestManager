"""Controle seguro da tarefa de notificações criada pelo instalador Windows."""

import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

from climatetest_manager.config import get_data_directory, is_synced_directory

TASK_NAME = "ClimateTestManager-Notifications"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _notification_action(data_directory: str = "") -> str:
    """Resolve o executável silencioso para diagnóstico e desenvolvimento."""

    candidates: list[tuple[Path, Path | None]] = []
    if getattr(sys, "frozen", False):
        candidates.append(
            (Path(sys.executable).resolve().with_name("ClimateTestNotifier.exe"), None)
        )
    project_root = _project_root()
    candidates.extend(
        [
            (project_root / "dist" / "ClimateTestManager-v0.8.0" / "ClimateTestNotifier.exe", None),
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
        "O notificador silencioso não foi encontrado. Repare a instalação do aplicativo."
    )


def _query_task_xml() -> bytes | str | None:
    result = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", TASK_NAME, "/XML"],
        capture_output=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return result.stdout if result.returncode == 0 else None


def _task_exists() -> bool:
    result = subprocess.run(
        ["schtasks.exe", "/Query", "/TN", TASK_NAME],
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return result.returncode == 0


def notification_task_installed() -> bool:
    """Confirma que a tarefa existe e está habilitada no Windows."""

    if sys.platform != "win32":
        return False
    task_xml_output = _query_task_xml()
    if task_xml_output is None:
        return False
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
    """Ativa ou desativa a tarefa existente sem trocar usuário, SID ou credenciais."""

    if sys.platform != "win32":
        raise RuntimeError("Os avisos em segundo plano estão disponíveis somente no Windows.")
    if enable and is_synced_directory(get_data_directory()):
        raise RuntimeError(
            "O banco SQLite ativo não deve ficar no OneDrive. "
            "Use o OneDrive somente para as cópias de segurança."
        )
    if not _task_exists():
        if not enable:
            return
        raise RuntimeError(
            "A tarefa de notificações do Windows não foi encontrada. "
            "Execute novamente o instalador do ClimateTest Manager e escolha "
            "Reparar/Atualizar; seus dados serão preservados."
        )

    command = [
        "schtasks.exe",
        "/Change",
        "/TN",
        TASK_NAME,
        "/ENABLE" if enable else "/DISABLE",
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        suffix = f" Detalhe do Windows: {detail}" if detail else ""
        raise RuntimeError(
            "O Windows não conseguiu alterar o estado da tarefa de notificações. "
            "Repare a instalação para restaurar a tarefa sem alterar seus dados." + suffix
        )
    if enable:
        subprocess.run(
            ["schtasks.exe", "/Run", "/TN", TASK_NAME],
            capture_output=True,
            text=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
