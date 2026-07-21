"""Criação do engine SQLite e inicialização do esquema local."""

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from climatetest_manager.config import get_database_path
from climatetest_manager.database.base import Base


def create_database_engine(database_path: Path | None = None) -> Engine:
    """Cria um engine SQLite com integridade referencial ativada."""

    resolved_path = (database_path or get_database_path()).expanduser().resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{resolved_path.as_posix()}")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Cria sessões que não expiram os objetos após cada commit."""

    return sessionmaker(bind=engine, expire_on_commit=False)


def initialize_database(database_path: Path | None = None) -> Engine:
    """Cria as tabelas ausentes e devolve o engine preparado."""

    # O import registra os modelos no metadata antes de create_all().
    from climatetest_manager.database import models  # noqa: F401

    engine = create_database_engine(database_path)
    Base.metadata.create_all(engine)
    return engine
