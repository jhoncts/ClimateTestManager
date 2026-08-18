import sys
import time

import pytest

from climatetest_manager.single_instance import SingleInstanceCoordinator


@pytest.mark.skipif(sys.platform != "win32", reason="Validação específica do mutex do Windows")
def test_second_windows_instance_signals_primary_instead_of_opening_again() -> None:
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
