"""Classe base compartilhada pelos modelos SQLAlchemy."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Registro central de metadados do banco."""
