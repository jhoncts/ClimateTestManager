"""Criação do engine SQLite e inicialização do esquema local."""

from contextlib import suppress
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from climatetest_manager.config import get_database_path
from climatetest_manager.database.base import Base
from climatetest_manager.database.migrations import SCHEMA_VERSION, migrate_database


def create_database_engine(database_path: Path | None = None) -> Engine:
    """Cria um engine SQLite com integridade referencial ativada."""

    resolved_path = (database_path or get_database_path()).expanduser().resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{resolved_path.as_posix()}",
        connect_args={"timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
        except Exception:
            # Se um PRAGMA falhar (por exemplo, em um arquivo corrompido),
            # a conexão ainda não pertence ao pool. Fechá-la explicitamente
            # evita manter o arquivo bloqueado no Windows.
            with suppress(Exception):
                cursor.close()
            with suppress(Exception):
                dbapi_connection.close()
            raise
        else:
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Cria sessões que não expiram os objetos após cada commit."""

    return sessionmaker(bind=engine, expire_on_commit=False)


def initialize_database(database_path: Path | None = None) -> Engine:
    """Cria as tabelas ausentes e devolve o engine preparado."""

    # Os imports registram todos os modelos no metadata antes de create_all().
    # O fluxo de frio vive em tabela própria para não reinterpretar nem alterar
    # silenciosamente registros criados nas versões anteriores.
    from climatetest_manager.database import cold_models, models  # noqa: F401

    engine = create_database_engine(database_path)
    try:
        with engine.connect() as connection:
            quick_check = connection.exec_driver_sql("PRAGMA quick_check").scalar()
    except Exception as error:
        engine.dispose()
        raise RuntimeError(
            "O banco de dados falhou na verificação de integridade e não será aberto. "
            "Restaure uma cópia verificada antes de continuar."
        ) from error
    if str(quick_check).casefold() != "ok":
        engine.dispose()
        raise RuntimeError(
            "O banco de dados falhou na verificação de integridade e não será aberto. "
            "Restaure uma cópia verificada antes de continuar."
        )
    migrate_database(engine)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(f"PRAGMA user_version={SCHEMA_VERSION}")
    return engine
