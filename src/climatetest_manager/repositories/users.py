"""Persistência local de usuários, sessões e eventos de segurança."""

from collections.abc import Callable
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from climatetest_manager.database.models import (
    AdministratorRecoveryRecord,
    SecurityAuditEvent,
    UserRecord,
    UserSessionRecord,
)


class UserRepository:
    """Isola os casos de uso de autenticação dos detalhes do SQLAlchemy."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def count_users(self) -> int:
        with self._session_factory() as session:
            return session.scalar(select(func.count(UserRecord.id))) or 0

    def count_active_admins(self) -> int:
        with self._session_factory() as session:
            return (
                session.scalar(
                    select(func.count(UserRecord.id)).where(
                        UserRecord.role == "admin",
                        UserRecord.is_active.is_(True),
                    )
                )
                or 0
            )

    def add(self, user: UserRecord) -> int:
        with self._session_factory() as session:
            session.add(user)
            session.commit()
            return user.id

    def get(self, user_id: int) -> UserRecord | None:
        with self._session_factory() as session:
            return session.get(UserRecord, user_id)

    def find_by_login(self, normalized_login: str) -> UserRecord | None:
        with self._session_factory() as session:
            statement = select(UserRecord).where(
                or_(
                    UserRecord.normalized_username == normalized_login,
                    UserRecord.normalized_email == normalized_login,
                )
            )
            return session.scalar(statement)

    def username_exists(self, normalized_username: str, *, excluding_id: int | None = None) -> bool:
        with self._session_factory() as session:
            statement = select(UserRecord.id).where(
                UserRecord.normalized_username == normalized_username
            )
            if excluding_id is not None:
                statement = statement.where(UserRecord.id != excluding_id)
            return session.scalar(statement) is not None

    def email_exists(self, normalized_email: str, *, excluding_id: int | None = None) -> bool:
        with self._session_factory() as session:
            statement = select(UserRecord.id).where(UserRecord.normalized_email == normalized_email)
            if excluding_id is not None:
                statement = statement.where(UserRecord.id != excluding_id)
            return session.scalar(statement) is not None

    def list_all(self) -> list[UserRecord]:
        with self._session_factory() as session:
            statement = select(UserRecord).order_by(
                UserRecord.is_active.desc(),
                UserRecord.first_name,
                UserRecord.last_name,
                UserRecord.id,
            )
            return list(session.scalars(statement))

    def list_active_emails(self) -> list[str]:
        """Retorna os destinatários autorizados, sem incluir contas desativadas."""

        with self._session_factory() as session:
            statement = (
                select(UserRecord.email)
                .where(UserRecord.is_active.is_(True))
                .order_by(UserRecord.email)
            )
            return list(dict.fromkeys(session.scalars(statement)))

    def list_active_admin_emails(self) -> list[str]:
        """Retorna somente os administradores ativos para alertas restritos."""

        with self._session_factory() as session:
            statement = (
                select(UserRecord.email)
                .where(
                    UserRecord.is_active.is_(True),
                    UserRecord.role == "admin",
                )
                .order_by(UserRecord.email)
            )
            return list(dict.fromkeys(session.scalars(statement)))

    def get_recovery_code_hash(self) -> str | None:
        with self._session_factory() as session:
            record = session.get(AdministratorRecoveryRecord, 1)
            return record.code_hash if record is not None else None

    def save_recovery_code_hash(self, code_hash: str, updated_at: datetime) -> None:
        with self._session_factory() as session:
            record = session.get(AdministratorRecoveryRecord, 1)
            if record is None:
                record = AdministratorRecoveryRecord(id=1, code_hash=code_hash)
                session.add(record)
            else:
                record.code_hash = code_hash
            record.updated_at = updated_at
            session.commit()

    def mutate(self, user_id: int, operation: Callable[[UserRecord], None]) -> None:
        with self._session_factory() as session:
            user = session.get(UserRecord, user_id)
            if user is None:
                raise LookupError(f"Usuário #{user_id} não encontrado.")
            operation(user)
            session.commit()

    def create_session(self, session_record: UserSessionRecord) -> None:
        with self._session_factory() as session:
            session.add(session_record)
            session.commit()

    def resolve_session(self, token_hash: str, now: datetime) -> UserRecord | None:
        with self._session_factory() as session:
            statement = (
                select(UserRecord)
                .join(UserSessionRecord, UserSessionRecord.user_id == UserRecord.id)
                .where(
                    UserSessionRecord.token_hash == token_hash,
                    UserSessionRecord.revoked_at.is_(None),
                    UserSessionRecord.expires_at > now,
                    UserRecord.is_active.is_(True),
                )
            )
            return session.scalar(statement)

    def revoke_session(self, token_hash: str, revoked_at: datetime) -> None:
        with self._session_factory() as session:
            record = session.scalar(
                select(UserSessionRecord).where(UserSessionRecord.token_hash == token_hash)
            )
            if record is None or record.revoked_at is not None:
                return
            record.revoked_at = revoked_at
            session.commit()

    def revoke_user_sessions(self, user_id: int, revoked_at: datetime) -> None:
        with self._session_factory() as session:
            records = session.scalars(
                select(UserSessionRecord).where(
                    UserSessionRecord.user_id == user_id,
                    UserSessionRecord.revoked_at.is_(None),
                )
            )
            for record in records:
                record.revoked_at = revoked_at
            session.commit()

    def add_security_event(
        self,
        *,
        actor_user_id: int | None,
        actor_label: str,
        action: str,
        target_user_id: int | None = None,
        details: str | None = None,
    ) -> None:
        with self._session_factory() as session:
            session.add(
                SecurityAuditEvent(
                    actor_user_id=actor_user_id,
                    actor_label=actor_label,
                    action=action,
                    target_user_id=target_user_id,
                    details=details,
                )
            )
            session.commit()
