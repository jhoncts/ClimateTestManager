"""Compatibilidade explícita entre cliente R6 e servidor central."""

import unittest
from unittest.mock import MagicMock, patch

import client_r6


class ClientR6Tests(unittest.TestCase):
    @patch("client_r6.urllib.request.urlopen")
    def test_reads_exact_r6_server_build_marker(self, urlopen: MagicMock) -> None:
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b"R6-20260813\n"
        urlopen.return_value = response

        value = client_r6._server_build("http://127.0.0.1:8550")

        self.assertEqual(value, client_r6.BUILD_REVISION)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8550/server-build.txt")

    @patch("client_r6.urllib.request.urlopen", side_effect=OSError("offline"))
    def test_missing_marker_is_treated_as_incompatible_server(self, _urlopen: MagicMock) -> None:
        self.assertEqual(client_r6._server_build("http://127.0.0.1:8550"), "")


if __name__ == "__main__":
    unittest.main()
