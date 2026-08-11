"""Coordenação de instância única do cliente desktop no Windows."""

from __future__ import annotations

import socket
import sys
import threading
from contextlib import suppress

_MUTEX_NAME = "ClimateTestManager.Desktop.Singleton.v1"
_ACTIVATION_PORT = 48550
_ACTIVATION_MESSAGE = b"SHOW\n"
_ERROR_ALREADY_EXISTS = 183


class SingleInstanceCoordinator:
    """Mantém uma única janela e transforma novas aberturas em pedido de foco."""

    def __init__(self) -> None:
        self.activation_requested = threading.Event()
        self._mutex_handle: int | None = None
        self._listener: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def acquire_or_signal(self) -> bool:
        """Retorna True no processo principal; o secundário só sinaliza e encerra."""

        if sys.platform != "win32":
            return True
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetLastError(0)
        handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
        if not handle:
            # Se o mutex do Windows não puder ser usado, não bloqueie o aplicativo.
            return True
        last_error = kernel32.GetLastError()
        if last_error == _ERROR_ALREADY_EXISTS:
            with suppress(Exception):
                self._signal_primary()
            kernel32.CloseHandle(handle)
            return False

        self._mutex_handle = int(handle)
        self._start_listener()
        return True

    def _start_listener(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("127.0.0.1", _ACTIVATION_PORT))
            listener.listen(4)
            listener.settimeout(0.5)
        except OSError:
            listener.close()
            return
        self._listener = listener
        self._thread = threading.Thread(
            target=self._listen,
            name="ClimateTestSingleInstance",
            daemon=True,
        )
        self._thread.start()

    def _listen(self) -> None:
        listener = self._listener
        if listener is None:
            return
        while not self._stop.is_set():
            try:
                connection, _address = listener.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            with connection:
                with suppress(OSError):
                    data = connection.recv(32)
                    if data.strip().upper() == _ACTIVATION_MESSAGE.strip():
                        self.activation_requested.set()

    @staticmethod
    def _signal_primary() -> None:
        for _attempt in range(12):
            try:
                with socket.create_connection(("127.0.0.1", _ACTIVATION_PORT), timeout=0.25) as sock:
                    sock.sendall(_ACTIVATION_MESSAGE)
                    return
            except OSError:
                threading.Event().wait(0.1)

    def consume_activation_request(self) -> bool:
        if not self.activation_requested.is_set():
            return False
        self.activation_requested.clear()
        return True

    def close(self) -> None:
        self._stop.set()
        listener = self._listener
        self._listener = None
        if listener is not None:
            with suppress(OSError):
                listener.close()
        handle = self._mutex_handle
        self._mutex_handle = None
        if handle and sys.platform == "win32":
            import ctypes

            with suppress(Exception):
                ctypes.windll.kernel32.ReleaseMutex(handle)
            with suppress(Exception):
                ctypes.windll.kernel32.CloseHandle(handle)

    def __enter__(self) -> SingleInstanceCoordinator:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
