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
from climatetest_manager.services.climate_tests import (
    ClimateTestService,
    CreateClimateTestCommand,
)
from climatetest_manager.single_instance import SingleInstanceCoordinator
from climatetest_manager.ui.components.table17 import build_table17_preview
from climatetest_manager.ui.offline import build_offline_view
from climatetest_manager.ui.responsive import LayoutProfile
from climatetest_manager.ui.shell import build_production_shell
from climatetest_manager.ui.theme import THEME_KEYS, AppColors
from climatetest_manager.ui.views.polished_new_test import PolishedNewTestView
from climatetest_manager.ui.views.polished_test_details import build_polished_test_details_view


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


def _text_values(control: ft.Control) -> list[str]:
    values: list[str] = []
    if isinstance(control, ft.Text) and control.value:
        values.append(control.value)
    child = getattr(control, "content", None)
    if isinstance(child, ft.Control):
        values.extend(_text_values(child))
    children = getattr(control, "controls", None)
    if isinstance(children, list):
        for item in children:
            if isinstance(item, ft.Control):
                values.extend(_text_values(item))
    return values


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


def test_production_shell_and_polished_views_build() -> None:
    with _DatabaseHarness() as harness:
        shell = build_production_shell(
            ft.Text("Conteúdo"),
            selected_view="dashboard",
            on_dashboard=lambda: None,
            on_tests=lambda: None,
            on_new_test=lambda: None,
            on_agenda=lambda: None,
            on_history=lambda: None,
            on_notifications=lambda: None,
            on_help=lambda: None,
            on_settings=lambda: None,
            on_users=lambda: None,
            on_logout=lambda: None,
            on_github=lambda: None,
            on_toggle_sidebar=lambda: None,
            current_user=harness.admin,
            layout=LayoutProfile.for_mode("regular"),
            notification_count=3,
        )
        assert isinstance(shell, ft.Row)

        new_test = PolishedNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
        assert isinstance(new_test.root, ft.Column)
        assert new_test.root.scroll == ft.ScrollMode.AUTO

        service = ClimateTestService(
            harness.repository,
            actor_provider=lambda: harness.admin.actor_label,
        )
        test_id = service.create(_test_command())
        details = service.get_details(test_id)
        details_view = build_polished_test_details_view(
            details,
            on_back=lambda: None,
            on_start_chamber=lambda _value: None,
            on_start_drying=lambda _value: None,
            on_finish=lambda _value: None,
            on_cancel=lambda _reason: None,
            on_edit=lambda: None,
            on_delete=lambda: None,
            on_admin_delete=lambda _reason: None,
            on_change_timestamp=lambda _name, _value, _reason: None,
        )
        assert isinstance(details_view, ft.Column)
        assert details_view.scroll == ft.ScrollMode.AUTO


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
    rendered_text = " ".join(_text_values(view)).casefold()
    assert "modo offline" in rendered_text
    assert "nenhuma alteração é permitida" in rendered_text
    assert "26800.1" in rendered_text


def test_single_instance_is_noop_outside_windows() -> None:
    if sys.platform == "win32":
        return
    coordinator = SingleInstanceCoordinator()
    try:
        assert coordinator.acquire_or_signal() is True
    finally:
        coordinator.close()
