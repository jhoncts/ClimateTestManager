"""Testes da configuração explícita do agente do Windows."""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from climatetest_manager.services.background import (
    configure_notification_task,
    notification_task_installed,
)


class BackgroundTaskTests(unittest.TestCase):
    def test_reports_task_as_installed_when_windows_query_succeeds(self) -> None:
        with (
            patch("climatetest_manager.services.background.sys.platform", "win32"),
            patch(
                "climatetest_manager.services.background.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ) as run,
        ):
            self.assertTrue(notification_task_installed())

        self.assertIn("/Query", run.call_args.args[0])

    def test_configures_task_only_after_explicit_call(self) -> None:
        result = SimpleNamespace(returncode=0, stdout="", stderr="")
        with (
            patch("climatetest_manager.services.background.sys.platform", "win32"),
            patch.dict("os.environ", {}, clear=True),
            patch(
                "climatetest_manager.services.background.subprocess.run",
                return_value=result,
            ) as run,
        ):
            configure_notification_task(enable=True)

        command = run.call_args.args[0]
        self.assertIn("install_notifier_task.ps1", " ".join(command))

    def test_rejects_background_configuration_outside_windows(self) -> None:
        with (
            patch("climatetest_manager.services.background.sys.platform", "linux"),
            self.assertRaisesRegex(RuntimeError, "somente no Windows"),
        ):
            configure_notification_task(enable=True)

    def test_scheduled_action_uses_no_console_executable(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        script = (project_root / "scripts" / "install_notifier_task.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("ClimateTestNotifier.exe", script)
        self.assertIn("pythonw.exe", script)
        self.assertNotIn('$taskCommand = "powershell.exe', script)


if __name__ == "__main__":
    unittest.main()
