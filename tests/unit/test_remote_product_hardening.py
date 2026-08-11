"""Regressões encontradas durante o primeiro uso real em rede local."""

import base64
from io import BytesIO
from unittest.mock import patch

import flet as ft
from PIL import Image

from climatetest_manager.client_bridge import DesktopToastCommand
from climatetest_manager.config import EmailSettings
from climatetest_manager.services.network import get_server_identity
from climatetest_manager.ui.components.dialogs import styled_dialog
from climatetest_manager.ui.components.helpers import _optimized_profile_photo_source


def test_smtp_can_be_tested_before_automatic_delivery_is_enabled() -> None:
    settings = EmailSettings(
        enabled=False,
        host="smtp.gmail.com",
        port=587,
        sender="admin@example.com",
        username="admin@example.com",
        password="abcdefghijklmnop",
        use_tls=True,
    )

    assert settings.has_credentials is True
    assert settings.is_configured is True
    assert settings.automatic_enabled is False


def test_profile_photo_is_compacted_to_small_data_uri() -> None:
    source_buffer = BytesIO()
    Image.new("RGB", (1254, 1254), (30, 120, 180)).save(source_buffer, format="PNG")
    original = source_buffer.getvalue()

    result = _optimized_profile_photo_source(base64.b64encode(original).decode("ascii"))

    assert result is not None
    prefix, encoded = result.split(",", 1)
    assert prefix == "data:image/webp;base64"
    optimized = base64.b64decode(encoded)
    assert len(optimized) < len(original)
    with Image.open(BytesIO(optimized)) as image:
        assert image.size == (256, 256)


def test_dialog_inputs_receive_remote_sync_handlers() -> None:
    description = ft.TextField()
    action = ft.TextField(multiline=True)
    enabled = ft.Switch(label="Ativo")
    content = ft.Column(controls=[description, action, enabled])

    styled_dialog(
        title="Teste",
        subtitle="Sincronização",
        icon=ft.Icons.BUG_REPORT_OUTLINED,
        content=content,
        actions=[],
    )

    assert description.on_change is not None
    assert action.on_change is not None
    assert enabled.on_change is not None


def test_desktop_toast_command_round_trip_preserves_accents() -> None:
    command = DesktopToastCommand(
        command_id="incident-42",
        title="Falha crítica",
        message="Amostra com alteração de condição.",
    )

    restored = DesktopToastCommand.from_json(command.to_json())

    assert restored == command


def test_server_identity_exposes_hostname_and_addresses() -> None:
    with (
        patch("climatetest_manager.services.network.socket.gethostname", return_value="LAB-SERVER"),
        patch(
            "climatetest_manager.services.network.local_ipv4_addresses",
            return_value=("192.168.1.50",),
        ),
    ):
        identity = get_server_identity(port=8550)

    assert identity.hostname == "LAB-SERVER"
    assert identity.addresses == ("192.168.1.50",)
    assert identity.preferred_url == "http://192.168.1.50:8550"
    assert identity.hostname_url == "http://LAB-SERVER:8550"
