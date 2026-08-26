import socket
import sys
import time
import uuid
from unittest.mock import patch

import pytest

from climatetest_manager.single_instance import SingleInstanceCoordinator


@pytest.mark.skipif(sys.platform != "win32", reason="Validação específica do mutex do Windows")
def test_second_windows_instance_signals_primary_instead_of_opening_again() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        activation_port = probe.getsockname()[1]
    mutex_name = rf"Local\ClimateTestManager-Test-{uuid.uuid4()}"

    with (
        patch("climatetest_manager.single_instance.DESKTOP_MUTEX_NAME", mutex_name),
        patch("climatetest_manager.single_instance.DESKTOP_ACTIVATION_PORT", activation_port),
    ):
        primary = SingleInstanceCoordinator()
        secondary = SingleInstanceCoordinator()
        try:
            assert primary.acquire_or_signal() is True
            assert secondary.acquire_or_signal() is False

            signaled = False
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                if primary.consume_activation_request():
                    signaled = True
                    break
                time.sleep(0.05)

            assert signaled is True
            assert primary.consume_activation_request() is False
            assert primary.activation_requested.is_set() is False
        finally:
            secondary.close()
            primary.close()
