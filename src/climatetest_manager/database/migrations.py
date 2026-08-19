"""Migrações SQLite pequenas e idempotentes para bancos criados nas versões anteriores."""

from sqlalchemy import Engine, inspect, text

SCHEMA_VERSION = 13

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

NOTIFICATION_COLUMNS = {
    "desktop_sent_at": "DATETIME",
    "email_sent_at": "DATETIME",
}

USER_COLUMNS = {
    "profile_photo_b64": "TEXT",
}

INCIDENT_COLUMNS = {
    "reason_code": "VARCHAR(80) NOT NULL DEFAULT 'other'",
    "admin_email_sent_at": "DATETIME",
    "admin_email_error": "TEXT",
}


def migrate_database(engine: Engine) -> None:
    """Adiciona campos operacionais sem apagar ou recriar tabelas existentes."""

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    with engine.begin() as connection:
        if "climate_tests" in table_names:
            existing = {column["name"] for column in inspector.get_columns("climate_tests")}
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
        for table_name, columns in (
            ("notification_events", NOTIFICATION_COLUMNS),
            ("users", USER_COLUMNS),
            ("system_incidents", INCIDENT_COLUMNS),
        ):
            if table_name not in table_names:
                continue
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type in columns.items():
                if column_name not in existing:
                    connection.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                    )
        connection.execute(text(f"PRAGMA user_version={SCHEMA_VERSION}"))
