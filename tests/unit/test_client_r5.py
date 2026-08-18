"""Validação do bloqueio de cliente R5 contra servidor antigo."""

import unittest
from unittest.mock import MagicMock, patch

import client_r5


class ClientR5Tests(unittest.TestCase):
    def test_reads_exact_server_build_marker(self) -> None:
        response = MagicMock()
        response.status = 200
        response.read.return_value = b"R5-20260812\n"
        response.__enter__.return_value = response
        response.__exit__.return_value = False

        with patch("client_r5.urllib.request.urlopen", return_value=response) as urlopen:
            build = client_r5._server_build("http://127.0.0.1:8550")

        self.assertEqual(build, client_r5.BUILD_REVISION)
        request = urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "http://127.0.0.1:8550/server-build.txt",
        )

    def test_missing_marker_is_treated_as_incompatible_server(self) -> None:
        with patch(
            "client_r5.urllib.request.urlopen",
            side_effect=OSError("not found"),
        ):
            self.assertEqual(client_r5._server_build("http://server:8550"), "")


if __name__ == "__main__":
    unittest.main()
