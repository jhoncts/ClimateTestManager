"""Migrações SQLite pequenas e idempotentes para bancos criados nas versões anteriores."""

from sqlalchemy import Engine, inspect, text

SCHEMA_VERSION = 8

OPERATIONAL_COLUMNS = {
    "chamber_started_at": "DATETIME",
    "chamber_nominal_end_at": "DATETIME",
    "chamber_maximum_end_at": "DATETIME",
    "chamber_ended_at": "DATETIME",
    "drying_started_at": "DATETIME",
    "drying_nominal_end_at": "DATETIME",
    "drying_maximum_end_at": "DATETIME",
    "drying_ended_at": "DATETIME",
    "finished_at": "DATETIME",
    "cancelled_at": "DATETIME",
    "cancellation_reason": "TEXT",
    "sample_quantity": "INTEGER NOT NULL DEFAULT 1",
    "input_mode": "VARCHAR(24) NOT NULL DEFAULT 'calculated'",
    "ts_reference": "VARCHAR(100)",
}


def migrate_database(engine: Engine) -> None:
    """Adiciona campos operacionais sem apagar ou recriar tabelas existentes."""

    inspector = inspect(engine)
    if "climate_tests" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("climate_tests")}
    with engine.begin() as connection:
        for column_name, column_type in OPERATIONAL_COLUMNS.items():
            if column_name not in existing:
                connection.execute(
                    text(f"ALTER TABLE climate_tests ADD COLUMN {column_name} {column_type}")
                )
        connection.execute(
            text(
                """
                UPDATE climate_tests
                SET input_mode = 'direct_configuration'
                WHERE input_mode IN ('plan_defined', 'plan_criterion')
                """
            )
        )
        connection.execute(text(f"PRAGMA user_version={SCHEMA_VERSION}"))
