"""Regressões encontradas durante o teste real da v0.8.0."""

from datetime import datetime

from climatetest_manager.services.auth import UserSummary
from climatetest_manager.ui.formatters import format_datetime
from climatetest_manager.ui.theme import THEME_OPTIONS


def _user(role: str) -> UserSummary:
    return UserSummary(
        id=1,
        username="teste",
        email="teste@example.com",
        first_name="Teste",
        last_name="Usuário",
        role=role,
        is_active=True,
        onboarding_completed=False,
        last_login_at=None,
        profile_photo_b64=None,
    )


def test_incident_utc_clock_is_presented_in_sao_paulo_time() -> None:
    assert format_datetime(datetime(2026, 8, 12, 10, 38), assume_utc=True) == "12/08/2026 07:38"


def test_operator_operates_and_viewer_is_read_only() -> None:
    operator = _user("operator")
    viewer = _user("viewer")
    assert operator.can_operate
    assert not operator.is_viewer
    assert viewer.is_viewer
    assert not viewer.can_operate
    assert viewer.role_label == "Consulta"


def test_theme_catalog_has_three_light_and_three_dark_options() -> None:
    keys = [item[0] for item in THEME_OPTIONS]
    assert keys == ["light", "amber", "ice", "dark", "graphite", "ocean"]
