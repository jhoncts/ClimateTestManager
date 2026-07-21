"""Testes da inicialização e persistência básica do SQLite."""

import unittest
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import inspect, select

from climatetest_manager.database.models import AuditEvent, ClimateTestRecord
from climatetest_manager.database.session import create_session_factory, initialize_database


class DatabaseTests(unittest.TestCase):
    def test_initializes_schema_and_persists_audit_event(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "test.db"
            engine = initialize_database(database_path)
            session_factory = create_session_factory(engine)

            self.assertEqual(
                set(inspect(engine).get_table_names()),
                {"climate_tests", "audit_events"},
            )

            climate_test = ClimateTestRecord(
                client="Cliente de teste",
                process_number="26000.1",
                product="Luminária",
                ex_marking="Ex db",
                epl="Gb",
                tamb_max_c=Decimal("40"),
                delta_t_max_k=Decimal("29.48"),
                service_temperature_c=Decimal("69.48"),
                selected_option="A",
            )
            climate_test.audit_events.append(
                AuditEvent(
                    actor="Operador de teste",
                    action="Ensaio criado",
                    reason="Validação automatizada",
                )
            )

            with session_factory() as session:
                session.add(climate_test)
                session.commit()

            with session_factory() as session:
                stored_test = session.scalar(select(ClimateTestRecord))

                self.assertIsNotNone(stored_test)
                self.assertEqual(stored_test.service_temperature_c, Decimal("69.48"))
                self.assertEqual(len(stored_test.audit_events), 1)


if __name__ == "__main__":
    unittest.main()
