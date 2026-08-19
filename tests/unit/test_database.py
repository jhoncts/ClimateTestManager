"""Testes da inicialização e persistência básica do SQLite."""

import unittest
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, inspect, select, text

from climatetest_manager.database.migrations import SCHEMA_VERSION
from climatetest_manager.database.models import AuditEvent, ClimateTestRecord
from climatetest_manager.database.session import create_session_factory, initialize_database


class DatabaseTests(unittest.TestCase):
    def test_refuses_to_open_a_corrupted_database(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "corrupted.db"
            database_path.write_bytes(b"nao e um banco sqlite")

            with self.assertRaisesRegex(RuntimeError, "verificação de integridade"):
                initialize_database(database_path)

            # No Windows, a remoção falha se a tentativa de abertura tiver
            # deixado uma conexão SQLite pendente.
            database_path.unlink()
            self.assertFalse(database_path.exists())

    def test_initializes_schema_and_persists_audit_event(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "test.db"
            engine = initialize_database(database_path)
            session_factory = create_session_factory(engine)

            try:
                self.assertEqual(
                    set(inspect(engine).get_table_names()),
                    {
                        "climate_tests",
                        "audit_events",
                        "climate_condition_snapshots",
                        "notification_events",
                        "notifier_run_state",
                        "resource_pauses",
                        "climate_test_pauses",
                        "users",
                        "user_sessions",
                        "security_audit_events",
                        "system_incidents",
                        "user_notification_reads",
                        "administrator_recovery",
                        "thermal_cold_workflows",
                    },
                )
                self.assertIn(
                    "profile_photo_b64",
                    {column["name"] for column in inspect(engine).get_columns("users")},
                )
                notification_columns = {
                    column["name"] for column in inspect(engine).get_columns("notification_events")
                }
                self.assertIn("desktop_sent_at", notification_columns)
                self.assertIn("email_sent_at", notification_columns)

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
            finally:
                engine.dispose()

    def test_migrates_v03_database_without_losing_existing_test(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "legacy.db"
            legacy_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
            with legacy_engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        CREATE TABLE climate_tests (
                            id INTEGER PRIMARY KEY,
                            client VARCHAR(160) NOT NULL,
                            process_number VARCHAR(80) NOT NULL,
                            product VARCHAR(200) NOT NULL,
                            ex_marking VARCHAR(240) NOT NULL,
                            epl VARCHAR(2) NOT NULL,
                            tamb_max_c NUMERIC(8, 2) NOT NULL,
                            delta_t_max_k NUMERIC(8, 2) NOT NULL,
                            service_temperature_c NUMERIC(8, 2) NOT NULL,
                            selected_option VARCHAR(1),
                            situation VARCHAR(24) NOT NULL,
                            notes TEXT,
                            normative_rule_version VARCHAR(40) NOT NULL,
                            created_at DATETIME NOT NULL,
                            updated_at DATETIME NOT NULL
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO climate_tests VALUES (
                            1, 'Cliente legado', '26000.1', 'Produto', '', 'Gb',
                            40, 35, 75, 'B', 'Aguardando', NULL, 'regra',
                            '2026-07-21 10:00:00', '2026-07-21 10:00:00'
                        )
                        """
                    )
                )
            legacy_engine.dispose()

            engine = initialize_database(database_path)
            try:
                columns = {item["name"] for item in inspect(engine).get_columns("climate_tests")}
                self.assertIn("chamber_started_at", columns)
                self.assertIn("cancellation_reason", columns)
                self.assertIn("thermal_cold_workflows", inspect(engine).get_table_names())
                with engine.connect() as connection:
                    self.assertEqual(
                        connection.scalar(text("SELECT client FROM climate_tests WHERE id=1")),
                        "Cliente legado",
                    )
                    self.assertEqual(
                        connection.scalar(text("SELECT COUNT(*) FROM thermal_cold_workflows")),
                        0,
                    )
                    self.assertEqual(
                        connection.scalar(text("PRAGMA user_version")),
                        SCHEMA_VERSION,
                    )
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
