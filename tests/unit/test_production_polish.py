"""Regressões da consolidação de produção da v0.8.0."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import flet as ft
from sqlalchemy import select

from climatetest_manager.database.models import SecurityAuditEvent, SystemIncidentRecord
from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.production import ProductionClimateTestRepository
from climatetest_manager.repositories.users import UserRepository
from climatetest_manager.services.auth import AuthenticationService, UserRegistrationCommand
from climatetest_manager.services.climate_tests import ClimateTestService, CreateClimateTestCommand
from climatetest_manager.single_instance import SingleInstanceCoordinator
from climatetest_manager.ui.components.table17 import build_table17_preview
from climatetest_manager.ui.offline import build_offline_view
from climatetest_manager.ui.theme import AppColors, THEME_KEYS


def _registration() -> UserRegistrationCommand:
    return UserRegistrationCommand(
        username="admin",
        email="admin@example.com",
        first_name="Administrador",
        last_name="Teste",
        password="Senha123",
        password_confirmation="Senha123",
        role="admin",
    )


def _test_command() -> CreateClimateTestCommand:
    return CreateClimateTestCommand(
        client="Cliente",
        process_number="26800.1",
        product="Invólucro",
        epl="Gb",
        tamb_max_c="40",
        delta_t_max_k="40",
        selected_option="B",
    )


class _DatabaseHarness:
    def __enter__(self):
        self.temporary_directory = TemporaryDirectory()
        self.engine = initialize_database(Path(self.temporary_directory.name) / "production.db")
        self.session_factory = create_session_factory(self.engine)
        self.repository = ProductionClimateTestRepository(self.session_factory)
        self.auth = AuthenticationService(UserRepository(self.session_factory))
        self.admin = self.auth.register_initial_admin(_registration())
        return self

    def __exit__(self, *_args: object) -> None:
        self.engine.dispose()
        self.temporary_directory.cleanup()


def test_repeated_incident_click_is_idempotent() -> None:
    with _DatabaseHarness() as harness:
        values = {
            "reason_code": "software_crash",
            "category": "Falha do software",
            "severity": "Alta",
            "description": "A interface parou durante uma operação de teste.",
            "immediate_action": "A operação foi interrompida e os dados foram conferidos.",
            "reported_by": harness.admin.actor_label,
        }

        first = harness.repository.report_system_incident(**values)
        second = harness.repository.report_system_incident(**values)

        assert first == second
        with harness.session_factory() as session:
            incidents = list(session.scalars(select(SystemIncidentRecord)))
        assert len(incidents) == 1


def test_notification_dismissal_is_per_user_without_deleting_incident() -> None:
    with _DatabaseHarness() as harness:
        incident_id = harness.repository.report_system_incident(
            reason_code="software_crash",
            category="Falha do software",
            severity="Alta",
            description="Falha técnica com conteúdo suficiente para registrar.",
            immediate_action="A atividade foi interrompida e o responsável foi avisado.",
            reported_by=harness.admin.actor_label,
        )
        before = harness.repository.list_user_notifications(
            user_id=harness.admin.id,
            is_admin=True,
        )
        assert any(item.source_id == incident_id for item in before)

        harness.repository.dismiss_user_notification(
            user_id=harness.admin.id,
            source_kind="incident",
            source_id=incident_id,
        )
        after = harness.repository.list_user_notifications(
            user_id=harness.admin.id,
            is_admin=True,
        )

        assert all(item.source_id != incident_id for item in after)
        with harness.session_factory() as session:
            assert session.get(SystemIncidentRecord, incident_id) is not None


def test_admin_delete_removes_test_but_preserves_security_audit() -> None:
    with _DatabaseHarness() as harness:
        service = ClimateTestService(
            harness.repository,
            actor_provider=lambda: harness.admin.actor_label,
        )
        test_id = service.create(_test_command())

        harness.repository.delete_test_as_administrator(
            test_id,
            actor_user_id=harness.admin.id,
            actor_label=harness.admin.actor_label,
            reason="Cadastro duplicado confirmado durante a validação interna.",
        )

        assert all(item.id != test_id for item in service.list_tests())
        with harness.session_factory() as session:
            audit = session.scalar(
                select(SecurityAuditEvent).where(
                    SecurityAuditEvent.action == "climate_test_deleted_by_admin"
                )
            )
        assert audit is not None
        assert f"Ensaio #{test_id}" in (audit.details or "")


def test_all_supported_themes_build_table17_preview() -> None:
    original_mode = "light"
    try:
        for mode in sorted(THEME_KEYS):
            AppColors.apply_mode(mode)
            preview = build_table17_preview("G1-HIGH-B")
            assert isinstance(preview, ft.Control)
    finally:
        AppColors.apply_mode(original_mode)


def test_offline_view_is_read_only_and_builds_with_snapshot() -> None:
    snapshot = {
        "saved_at": "2026-08-11T12:00:00",
        "user": {"name": "Operador", "role": "Operador"},
        "summary": {"in_progress": 1, "waiting": 2, "paused": 0, "overdue": 0},
        "tests": [
            {
                "id": 1,
                "client": "Cliente",
                "process_number": "26800.1",
                "product": "Invólucro",
                "situation": "Na Câmara",
                "deadline": "No prazo",
                "nominal_end_at": "2026-08-20T12:00",
            }
        ],
    }

    view = build_offline_view(
        snapshot,
        server_url="http://192.168.1.20:8550",
        on_retry=lambda _event: None,
    )

    assert isinstance(view, ft.Container)
    assert "offline" in str(view.content).casefold()


def test_single_instance_is_noop_outside_windows() -> None:
    if sys.platform == "win32":
        return
    coordinator = SingleInstanceCoordinator()
    try:
        assert coordinator.acquire_or_signal() is True
    finally:
        coordinator.close()
