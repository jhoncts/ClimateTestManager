"""Testes do registro de falhas e ações corretivas do sistema."""

import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.climate_tests import ClimateTestRepository
from climatetest_manager.repositories.users import UserRepository
from climatetest_manager.services.auth import AuthenticationService, UserRegistrationCommand
from climatetest_manager.services.climate_tests import (
    ClimateTestService,
    CreateClimateTestCommand,
)
from climatetest_manager.services.notifications import deliver_pending_incident_emails


class RecordingEmailProvider:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send(self, title: str, message: str) -> None:
        self.messages.append((title, message))


class SystemIncidentTests(unittest.TestCase):
    def test_parallel_clients_can_write_incidents_without_sharing_sessions(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            engine = initialize_database(Path(temporary_directory) / "parallel.db")
            repository = ClimateTestRepository(create_session_factory(engine))

            def report(index: int) -> int:
                return repository.report_system_incident(
                    reason_code="performance",
                    category="Lentidão, congelamento ou demora excessiva",
                    severity="Média",
                    description=f"Relato simultâneo da estação de trabalho número {index}.",
                    immediate_action="A operação foi anotada e a tela mantida sem alterações.",
                    reported_by=f"Operador {index} (@operador{index})",
                )

            try:
                with ThreadPoolExecutor(max_workers=6) as executor:
                    incident_ids = list(executor.map(report, range(12)))

                self.assertEqual(len(set(incident_ids)), 12)
                self.assertEqual(len(repository.list_system_incidents(limit=20)), 12)
            finally:
                engine.dispose()

    def test_preserves_original_report_when_admin_resolves_incident(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            engine = initialize_database(Path(temporary_directory) / "incidents.db")
            repository = ClimateTestRepository(create_session_factory(engine))
            try:
                incident_id = repository.report_system_incident(
                    category="Backup ou restauração",
                    severity="Alto",
                    description="A cópia externa não foi criada na verificação diária.",
                    immediate_action="O uso foi mantido com uma cópia manual verificada.",
                    reported_by="Operador Teste (@operador)",
                )
                resolved_at = datetime(2026, 8, 3, 15, 0, tzinfo=UTC)
                repository.resolve_system_incident(
                    incident_id,
                    corrective_action=(
                        "Destino corrigido, restauração simulada e conteúdo conferido."
                    ),
                    resolved_by="Admin Local (@admin)",
                    resolved_at=resolved_at,
                )

                incident = repository.list_system_incidents()[0]
                self.assertEqual(
                    incident.description, ("A cópia externa não foi criada na verificação diária.")
                )
                self.assertEqual(
                    incident.immediate_action,
                    "O uso foi mantido com uma cópia manual verificada.",
                )
                self.assertEqual(incident.status, "resolved")
                self.assertEqual(incident.resolved_at, resolved_at.replace(tzinfo=None))
                self.assertIn("restauração simulada", incident.corrective_action or "")
            finally:
                engine.dispose()

    def test_cannot_resolve_same_incident_twice(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            engine = initialize_database(Path(temporary_directory) / "incidents.db")
            repository = ClimateTestRepository(create_session_factory(engine))
            try:
                incident_id = repository.report_system_incident(
                    category="Falha do software",
                    severity="Médio",
                    description="A tela não abriu durante a operação programada.",
                    immediate_action="O horário foi anotado no formulário controlado.",
                    reported_by="Operador Teste (@operador)",
                )
                repository.resolve_system_incident(
                    incident_id,
                    corrective_action="Correção instalada e fluxo repetido com resultado aprovado.",
                    resolved_by="Admin Local (@admin)",
                )

                with self.assertRaisesRegex(ValueError, "já foi encerrada"):
                    repository.resolve_system_incident(
                        incident_id,
                        corrective_action="Tentativa de sobrescrever a conclusão anterior.",
                        resolved_by="Outro Admin (@outro)",
                    )
            finally:
                engine.dispose()

    def test_incident_is_admin_only_and_operational_notice_reaches_both_profiles(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            engine = initialize_database(Path(temporary_directory) / "notifications.db")
            session_factory = create_session_factory(engine)
            repository = ClimateTestRepository(session_factory)
            auth = AuthenticationService(UserRepository(session_factory))
            try:
                admin = auth.register_initial_admin(
                    UserRegistrationCommand(
                        username="admin",
                        email="admin@example.com",
                        first_name="Admin",
                        last_name="Local",
                        password="Senha123",
                        password_confirmation="Senha123",
                    )
                )
                operator = auth.create_user(
                    admin,
                    UserRegistrationCommand(
                        username="operador",
                        email="operador@example.com",
                        first_name="Operador",
                        last_name="Teste",
                        password="Senha123",
                        password_confirmation="Senha123",
                    ),
                )
                now = datetime(2026, 8, 10, 8, 0)
                service = ClimateTestService(repository, now_provider=lambda: now)
                test_id = service.create(
                    CreateClimateTestCommand(
                        client="Cliente",
                        process_number="26999.9",
                        product="Amostra",
                        epl="Gb",
                        tamb_max_c="40",
                        delta_t_max_k="35",
                        selected_option="B",
                    )
                )
                service.start_chamber(test_id)
                incident_id = repository.report_system_incident(
                    reason_code="notifications",
                    category="Aviso, notificação do Windows ou e-mail não enviado",
                    severity="Média",
                    description="O aviso esperado não apareceu no computador do laboratório.",
                    immediate_action="O prazo foi conferido manualmente na agenda do sistema.",
                    reported_by=operator.actor_label,
                )
                due_time = now + timedelta(hours=502)

                admin_notifications = repository.list_user_notifications(
                    user_id=admin.id,
                    is_admin=True,
                    now=due_time,
                )
                operator_notifications = repository.list_user_notifications(
                    user_id=operator.id,
                    is_admin=False,
                    now=due_time,
                )

                self.assertTrue(any(item.source_kind == "incident" for item in admin_notifications))
                self.assertFalse(
                    any(item.source_kind == "incident" for item in operator_notifications)
                )
                self.assertTrue(
                    any(item.source_kind == "operation" for item in admin_notifications)
                )
                self.assertTrue(
                    any(item.source_kind == "operation" for item in operator_notifications)
                )
                repository.mark_user_notification_read(
                    user_id=admin.id,
                    source_kind="incident",
                    source_id=incident_id,
                )
                refreshed = repository.list_user_notifications(
                    user_id=admin.id,
                    is_admin=True,
                    now=due_time,
                )
                self.assertTrue(
                    next(item for item in refreshed if item.source_kind == "incident").is_read
                )

                email = RecordingEmailProvider()
                self.assertEqual(
                    deliver_pending_incident_emails(
                        repository,
                        email,
                        now_provider=lambda: due_time,
                    ),
                    (1, 0),
                )
                self.assertEqual(len(email.messages), 1)
                self.assertIn("Prioridade Média", email.messages[0][0])
                self.assertEqual(
                    deliver_pending_incident_emails(repository, email),
                    (0, 0),
                )
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
