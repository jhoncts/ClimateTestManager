"""Descoberta simples e segura do servidor central na rede local."""

from __future__ import annotations

import ipaddress
import json
import socket
from dataclasses import dataclass
from threading import Event, Thread

from climatetest_manager import __version__

DISCOVERY_PORT = 8551
DISCOVERY_REQUEST = b"CLIMATETEST_DISCOVER_V1"
DEFAULT_APP_PORT = 8550


@dataclass(frozen=True, slots=True)
class ServerIdentity:
    """Informações legíveis para instalar e diagnosticar estações."""

    hostname: str
    addresses: tuple[str, ...]
    port: int = DEFAULT_APP_PORT

    @property
    def preferred_address(self) -> str:
        return self.addresses[0] if self.addresses else self.hostname

    @property
    def preferred_url(self) -> str:
        return f"http://{self.preferred_address}:{self.port}"

    @property
    def hostname_url(self) -> str:
        return f"http://{self.hostname}:{self.port}"


def _valid_ipv4(value: str) -> ipaddress.IPv4Address | None:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return None
    if not isinstance(address, ipaddress.IPv4Address):
        return None
    if address.is_loopback or address.is_unspecified or address.is_multicast:
        return None
    return address


def local_ipv4_addresses() -> tuple[str, ...]:
    """Obtém endereços IPv4 úteis sem depender de acesso à internet."""

    candidates: set[str] = set()
    hostname = socket.gethostname()
    try:
        for item in socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_DGRAM):
            candidate = item[4][0]
            if _valid_ipv4(candidate) is not None:
                candidates.add(candidate)
    except OSError:
        pass

    # A conexão UDP não transmite dados; apenas pede ao Windows a rota/interface preferida.
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))
        candidate = probe.getsockname()[0]
        if _valid_ipv4(candidate) is not None:
            candidates.add(candidate)
    except OSError:
        pass
    finally:
        probe.close()

    def sort_key(value: str) -> tuple[int, int]:
        address = ipaddress.ip_address(value)
        return (0 if address.is_private else 1, int(address))

    return tuple(sorted(candidates, key=sort_key))


def get_server_identity(*, port: int = DEFAULT_APP_PORT) -> ServerIdentity:
    return ServerIdentity(
        hostname=socket.gethostname() or "ClimateTest-Server",
        addresses=local_ipv4_addresses(),
        port=port,
    )


class DiscoveryResponder:
    """Responde somente a uma assinatura conhecida por UDP dentro da LAN."""

    def __init__(self, *, app_port: int = DEFAULT_APP_PORT, discovery_port: int = DISCOVERY_PORT):
        self._app_port = app_port
        self._discovery_port = discovery_port
        self._stop = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._run, name="ClimateTestDiscovery", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        identity = get_server_identity(port=self._app_port)
        payload = json.dumps(
            {
                "service": "ClimateTestManager",
                "protocol": 1,
                "hostname": identity.hostname,
                "port": identity.port,
                "version": __version__,
            },
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", self._discovery_port))
            sock.settimeout(0.8)
            while not self._stop.is_set():
                try:
                    data, remote = sock.recvfrom(1024)
                except TimeoutError:
                    continue
                except OSError:
                    break
                if data.strip() != DISCOVERY_REQUEST:
                    continue
                try:
                    sock.sendto(payload, remote)
                except OSError:
                    continue
        except OSError:
            # O servidor principal continua funcional mesmo se a descoberta estiver bloqueada.
            return
        finally:
            sock.close()
