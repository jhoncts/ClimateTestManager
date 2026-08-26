"""Identidade exclusiva; deve ser diferente em cada produto da família."""

from __future__ import annotations

import hashlib

PRODUCT_ID = "com.jhoncts.climatetestmanager"
PRODUCT_NAME = "ClimateTest Manager"
SERVICE_NAME = "ClimateTestManager"
SERVER_IDENTITY_PATH = "/climatetest-server.json"
SERVER_PROTOCOL_VERSION = 1
DEFAULT_APP_PORT = 8550
DISCOVERY_PORT = 8551
DISCOVERY_REQUEST = b"CLIMATETEST_DISCOVER_V1"


def desktop_activation_port(product_id: str = PRODUCT_ID) -> int:
    """Deriva uma porta loopback estável do ID, evitando números copiados entre produtos."""

    digest = hashlib.sha256(product_id.encode("utf-8")).digest()
    return 49152 + (int.from_bytes(digest[:4], "big") % 12000)


DESKTOP_MUTEX_NAME = f"Local\\{PRODUCT_ID}.Desktop.Singleton.v1"
DESKTOP_ACTIVATION_PORT = desktop_activation_port()
DESKTOP_ACTIVATION_MESSAGE = f"SHOW {PRODUCT_ID}\n".encode("ascii")
