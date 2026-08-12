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
    def test_reports_task_as_active_when_windows_task_is_enabled(self) -> None:
        task_xml = (
            '<?xml version="1.0" encoding="UTF-16"?>'
            '<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">'
            "<Settings><Enabled>true</Enabled></Settings>"
            "</Task>"
        ).encode("utf-16")
        with (
            patch("climatetest_manager.services.background.sys.platform", "win32"),
            patch(
                "climatetest_manager.services.background.subprocess.run",
                return_value=SimpleNamespace(returncode=0, stdout=task_xml),
            ) as run,
        ):
            self.assertTrue(notification_task_installed())

        self.assertIn("/Query", run.call_args.args[0])
        self.assertIn("/XML", run.call_args.args[0])
        self.assertNotIn("text", run.call_args.kwargs)

    def test_uses_windows_default_when_enabled_element_is_omitted(self) -> None:
        task_xml = b"""\
        <Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
          <Settings />
        </Task>
        """
        with (
            patch("climatetest_manager.services.background.sys.platform", "win32"),
            patch(
                "climatetest_manager.services.background.subprocess.run",
                return_value=SimpleNamespace(returncode=0, stdout=task_xml),
            ),
        ):
            self.assertTrue(notification_task_installed())

    def test_accepts_windows_xml_with_mismatched_utf16_declaration(self) -> None:
        task_xml = (
            b'<?xml version="1.0" encoding="UTF-16"?>\r\r\n'
            b'<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">'
            b"<Settings /></Task>"
        )
        with (
            patch("climatetest_manager.services.background.sys.platform", "win32"),
            patch(
                "climatetest_manager.services.background.subprocess.run",
                return_value=SimpleNamespace(returncode=0, stdout=task_xml),
            ),
        ):
            self.assertTrue(notification_task_installed())

    def test_reports_disabled_windows_task_as_inactive(self) -> None:
        task_xml = b"""\
        <Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
          <Settings><Enabled>false</Enabled></Settings>
        </Task>
        """
        with (
            patch("climatetest_manager.services.background.sys.platform", "win32"),
            patch(
                "climatetest_manager.services.background.subprocess.run",
                return_value=SimpleNamespace(returncode=0, stdout=task_xml),
            ),
        ):
            self.assertFalse(notification_task_installed())

    def test_reports_unreadable_windows_task_as_inactive(self) -> None:
        with (
            patch("climatetest_manager.services.background.sys.platform", "win32"),
            patch(
                "climatetest_manager.services.background.subprocess.run",
                return_value=SimpleNamespace(returncode=0, stdout=b"saida invalida"),
            ),
        ):
            self.assertFalse(notification_task_installed())

    def test_enables_existing_task_without_recreating_principal(self) -> None:
        result = SimpleNamespace(returncode=0, stdout="", stderr="")
        with (
            patch("climatetest_manager.services.background.sys.platform", "win32"),
            patch(
                "climatetest_manager.services.background.subprocess.run",
                return_value=result,
            ) as run,
        ):
            configure_notification_task(enable=True)

        commands = [call.args[0] for call in run.call_args_list]
        self.assertTrue(any("/ENABLE" in command for command in commands))
        self.assertFalse(any("/Create" in command for command in commands))

    def test_rejects_background_configuration_outside_windows(self) -> None:
        with (
            patch("climatetest_manager.services.background.sys.platform", "linux"),
            self.assertRaisesRegex(RuntimeError, "somente no Windows"),
        ):
            configure_notification_task(enable=True)

    def test_rejects_active_database_inside_onedrive(self) -> None:
        with (
            patch("climatetest_manager.services.background.sys.platform", "win32"),
            patch.dict(
                "os.environ",
                {"CLIMATETEST_DATA_DIR": "C:\\Users\\Teste\\OneDrive\\dados"},
            ),
            self.assertRaisesRegex(RuntimeError, "OneDrive"),
        ):
            configure_notification_task(enable=True)

    def test_disables_existing_task_without_deleting_it(self) -> None:
        result = SimpleNamespace(returncode=0, stdout="", stderr="")
        with (
            patch("climatetest_manager.services.background.sys.platform", "win32"),
            patch(
                "climatetest_manager.services.background.subprocess.run",
                return_value=result,
            ) as run,
        ):
            configure_notification_task(enable=False)

        commands = [call.args[0] for call in run.call_args_list]
        self.assertTrue(any("/DISABLE" in command for command in commands))
        self.assertFalse(any("/Delete" in command for command in commands))

    def test_scheduled_action_uses_no_console_executable(self) -> None:
        executable = Path("C:/Aplicativo/ClimateTestNotifier.exe")
        with (
            patch("climatetest_manager.services.background.sys.frozen", True, create=True),
            patch(
                "climatetest_manager.services.background.sys.executable",
                str(executable.with_name("ClimateTestManager.exe")),
            ),
            patch.object(Path, "exists", return_value=True),
        ):
            from climatetest_manager.services.background import _notification_action

            action = _notification_action()

        self.assertIn("ClimateTestNotifier.exe", action)
        self.assertNotIn("powershell", action.casefold())
        self.assertNotIn("cmd.exe", action.casefold())


if __name__ == "__main__":
    unittest.main()
