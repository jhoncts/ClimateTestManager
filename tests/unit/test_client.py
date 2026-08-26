"""Regressões do executável desktop que conecta ao servidor central."""

import inspect
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import client


class DesktopClientTests(unittest.TestCase):
    def test_page_handler_is_really_async(self) -> None:
        """O Flet precisa receber uma coroutine function, não uma lambda que devolve coroutine."""

        handler = client._build_page_handler("http://localhost:8550")
        self.assertTrue(inspect.iscoroutinefunction(handler))

    def test_server_name_is_normalized_with_default_port(self) -> None:
        self.assertEqual(
            client._normalize_server_url("LAB-SERVER"),
            "http://lab-server:8550",
        )

    def test_explicit_port_is_preserved(self) -> None:
        self.assertEqual(
            client._normalize_server_url("http://127.0.0.1:18550/"),
            "http://127.0.0.1:18550",
        )

    def test_installer_server_file_is_used_when_url_is_not_passed(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_directory = root / "ClimateTestManager"
            config_directory.mkdir(parents=True)
            (config_directory / "server.url").write_text(
                "http://LAB-SERVER:8550\n",
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"PROGRAMDATA": str(root)}, clear=False):
                self.assertEqual(
                    client._resolve_server_url(),
                    "http://lab-server:8550",
                )

    def test_command_line_url_overrides_installer_configuration(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_directory = root / "ClimateTestManager"
            config_directory.mkdir(parents=True)
            (config_directory / "server.url").write_text(
                "http://wrong-server:8550",
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"PROGRAMDATA": str(root)}, clear=False):
                self.assertEqual(
                    client._resolve_server_url("10.0.0.25"),
                    "http://10.0.0.25:8550",
                )

    def test_ready_marker_is_written_atomically(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            marker = Path(temporary_directory) / "desktop.ready"
            client._write_ready_marker(marker, "http://localhost:8550")
            self.assertTrue(marker.exists())
            self.assertIn("ClimateTest Manager", marker.read_text(encoding="utf-8"))

    @patch("client.urllib.request.urlopen")
    def test_server_available_requires_exact_product_identity(self, urlopen) -> None:
        response = urlopen.return_value.__enter__.return_value
        response.status = 200
        response.read.return_value = json.dumps(
            {
                "product_id": "com.jhoncts.climatetestmanager",
                "service": "ClimateTestManager",
                "protocol": 1,
            }
        ).encode("utf-8")

        self.assertTrue(client._server_available("http://127.0.0.1:8550"))
        request = urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "http://127.0.0.1:8550/climatetest-server.json",
        )

        response.read.return_value = json.dumps(
            {
                "product_id": "com.jhoncts.calibralab",
                "service": "CalibraLab",
                "protocol": 1,
            }
        ).encode("utf-8")
        self.assertFalse(client._server_available("http://127.0.0.1:8765"))


if __name__ == "__main__":
    unittest.main()
