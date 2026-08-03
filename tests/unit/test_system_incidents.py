"""Testes do registro de falhas e ações corretivas do sistema."""

import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.climate_tests import ClimateTestRepository


class SystemIncidentTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
