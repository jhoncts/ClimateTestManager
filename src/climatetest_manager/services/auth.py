"""Autenticação local, perfis e gerenciamento seguro das contas."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from climatetest_manager.database.models import UserRecord, UserSessionRecord
from climatetest_manager.repositories.users import UserRepository
from climatetest_manager.services.profile_photos import (
    ProfilePhotoError,
    optimize_profile_photo,
)

PBKDF2_ITERATIONS = 600_000
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,32}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthenticationError(ValueError):
    """Erro seguro que pode ser apresentado na interface."""


@dataclass(frozen=True, slots=True)
class UserSummary:
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    onboarding_completed: bool
    last_login_at: datetime | None
    profile_photo_b64: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def actor_label(self) -> str:
        return f"{self.full_name} (@{self.username})"

    @property
    def role_label(self) -> str:
        if self.is_admin:
            return "Administrador"
        if self.is_viewer:
            return "Consulta"
        return "Operador"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_viewer(self) -> bool:
        return self.role == "viewer"

    @property
    def can_operate(self) -> bool:
        return self.role in {"admin", "operator"}


@dataclass(frozen=True, slots=True)
class UserRegistrationCommand:
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    password_confirmation: str
    role: str = "operator"


@dataclass(frozen=True, slots=True)
class UserUpdateCommand:
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    user: UserSummary
    token: str
    remember: bool


def _normalize(value: str) -> str:
    return value.strip().casefold()


def _required(value: str, label: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise AuthenticationError(f"{label} é obrigatório.")
    return normalized


def _validate_password(password: str, confirmation: str) -> str:
    if password != confirmation:
        raise AuthenticationError("A confirmação da senha não confere.")
    if len(password) < 8:
        raise AuthenticationError("A senha precisa ter pelo menos 8 caracteres.")
    if not any(character.isalpha() for character in password):
        raise AuthenticationError("A senha precisa conter pelo menos uma letra.")
    if not any(character.isdigit() for character in password):
        raise AuthenticationError("A senha precisa conter pelo menos um número.")
    return password


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return "$".join(
        (
            "pbkdf2_sha256",
            str(PBKDF2_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, encoded_salt, encoded_digest = encoded.split("$", maxsplit=3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
        calculated = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(calculated, expected)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _recovery_hash(code: str) -> str:
    normalized = "".join(code.strip().upper().split())
    return hashlib.sha256(normalized.encode("ascii", errors="ignore")).hexdigest()


def _new_recovery_code() -> str:
    """Gera um código legível sem caracteres visualmente ambíguos."""

    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    payload = "".join(secrets.choice(alphabet) for _ in range(20))
    return "CTM-" + "-".join(payload[index : index + 4] for index in range(0, 20, 4))


def _summary(user: UserRecord) -> UserSummary:
    return UserSummary(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        is_active=user.is_active,
        onboarding_completed=user.onboarding_completed_at is not None,
        last_login_at=user.last_login_at,
        profile_photo_b64=user.profile_photo_b64,
    )


class AuthenticationService:
    """Coordena primeiro acesso, login, sessões e administração das contas."""

    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def requires_initial_setup(self) -> bool:
        return self._repository.count_users() == 0

    def has_administrator_recovery_code(self) -> bool:
        return self._repository.get_recovery_code_hash() is not None

    def _validated_identity(
        self,
        command: UserRegistrationCommand | UserUpdateCommand,
        *,
        excluding_id: int | None = None,
    ) -> tuple[str, str, str, str, str, str]:
        username = _required(command.username, "Nome de usuário")
        normalized_username = _normalize(username)
        if not USERNAME_PATTERN.fullmatch(username):
            raise AuthenticationError(
                "O usuário deve ter de 3 a 32 caracteres: letras, números, ponto, hífen ou _."
            )
        email = _required(command.email, "E-mail")
        normalized_email = _normalize(email)
        if not EMAIL_PATTERN.fullmatch(email):
            raise AuthenticationError("Informe um e-mail válido.")
        if self._repository.username_exists(
            normalized_username,
            excluding_id=excluding_id,
        ):
            raise AuthenticationError("Este nome de usuário já está cadastrado.")
        if self._repository.email_exists(normalized_email, excluding_id=excluding_id):
            raise AuthenticationError("Este e-mail já está cadastrado.")
        first_name = _required(command.first_name, "Nome")
        last_name = _required(command.last_name, "Sobrenome")
        return (
            username,
            normalized_username,
            email,
            normalized_email,
            first_name,
            last_name,
        )

    def register_initial_admin(self, command: UserRegistrationCommand) -> UserSummary:
        if not self.requires_initial_setup():
            raise AuthenticationError("O administrador inicial já foi cadastrado.")
        user = self._build_user(command, forced_role="admin")
        self._repository.add(user)
        self._repository.add_security_event(
            actor_user_id=user.id,
            actor_label=_summary(user).actor_label,
            action="Administrador inicial cadastrado",
            target_user_id=user.id,
        )
        return _summary(user)

    def rotate_administrator_recovery_code(
        self,
        actor: UserSummary | None = None,
    ) -> str:
        """Substitui o código anterior e devolve o novo valor uma única vez."""

        if actor is not None:
            self._require_admin(actor)
        code = _new_recovery_code()
        now = datetime.now(UTC)
        self._repository.save_recovery_code_hash(_recovery_hash(code), now)
        self._repository.add_security_event(
            actor_user_id=actor.id if actor is not None else None,
            actor_label=(
                actor.actor_label if actor is not None else "Configuração local do servidor"
            ),
            action="Código de recuperação do administrador renovado",
            target_user_id=actor.id if actor is not None else None,
        )
        return code

    def recover_administrator(
        self,
        recovery_code: str,
        command: UserRegistrationCommand,
    ) -> tuple[UserSummary, str]:
        """Recupera a conta principal; a UI só expõe esta ação no próprio servidor."""

        expected_hash = self._repository.get_recovery_code_hash()
        if not expected_hash or not hmac.compare_digest(
            expected_hash,
            _recovery_hash(recovery_code),
        ):
            raise AuthenticationError("Código de recuperação inválido.")
        candidates = self._repository.list_all()
        target = next(
            (user for user in candidates if user.role == "admin" and user.is_active),
            next((user for user in candidates if user.role == "admin"), None),
        )
        if target is None:
            raise AuthenticationError("Não existe uma conta administradora para recuperar.")
        (
            username,
            normalized_username,
            email,
            normalized_email,
            first_name,
            last_name,
        ) = self._validated_identity(command, excluding_id=target.id)
        password = _validate_password(command.password, command.password_confirmation)

        def operation(record: UserRecord) -> None:
            record.username = username
            record.normalized_username = normalized_username
            record.email = email
            record.normalized_email = normalized_email
            record.first_name = first_name
            record.last_name = last_name
            record.password_hash = _hash_password(password)
            record.role = "admin"
            record.is_active = True

        self._repository.mutate(target.id, operation)
        now = datetime.now(UTC)
        self._repository.revoke_user_sessions(target.id, now)
        refreshed = self._repository.get(target.id)
        if refreshed is None:
            raise AuthenticationError("Não foi possível recuperar o administrador.")
        recovered = _summary(refreshed)
        self._repository.add_security_event(
            actor_user_id=None,
            actor_label="Recuperação local do servidor",
            action="Administrador principal recuperado",
            target_user_id=recovered.id,
            details=recovered.actor_label,
        )
        return recovered, self.rotate_administrator_recovery_code()

    def _build_user(
        self,
        command: UserRegistrationCommand,
        *,
        forced_role: str | None = None,
    ) -> UserRecord:
        (
            username,
            normalized_username,
            email,
            normalized_email,
            first_name,
            last_name,
        ) = self._validated_identity(command)
        password = _validate_password(command.password, command.password_confirmation)
        role = forced_role or command.role
        if role not in {"admin", "operator", "viewer"}:
            raise AuthenticationError("Perfil de usuário inválido.")
        return UserRecord(
            username=username,
            normalized_username=normalized_username,
            email=email,
            normalized_email=normalized_email,
            first_name=first_name,
            last_name=last_name,
            password_hash=_hash_password(password),
            role=role,
            is_active=True,
        )

    def authenticate(
        self,
        login: str,
        password: str,
        *,
        remember: bool,
    ) -> AuthenticatedSession:
        normalized_login = _normalize(login)
        user = self._repository.find_by_login(normalized_login)
        if user is None or not user.is_active or not _verify_password(password, user.password_hash):
            raise AuthenticationError("Usuário/e-mail ou senha inválidos.")
        now = datetime.now(UTC)
        self._repository.mutate(user.id, lambda target: setattr(target, "last_login_at", now))
        token = secrets.token_urlsafe(32)
        duration = timedelta(days=30) if remember else timedelta(hours=12)
        self._repository.create_session(
            UserSessionRecord(
                user_id=user.id,
                token_hash=_token_hash(token),
                expires_at=now + duration,
            )
        )
        refreshed = self._repository.get(user.id)
        if refreshed is None:
            raise AuthenticationError("Não foi possível carregar o usuário autenticado.")
        self._repository.add_security_event(
            actor_user_id=user.id,
            actor_label=_summary(refreshed).actor_label,
            action="Login realizado",
            target_user_id=user.id,
            details="Sessão persistente" if remember else "Sessão temporária",
        )
        return AuthenticatedSession(_summary(refreshed), token, remember)

    def restore_session(self, token: str) -> UserSummary | None:
        user = self._repository.resolve_session(_token_hash(token), datetime.now(UTC))
        return _summary(user) if user is not None else None

    def logout(self, token: str | None, user: UserSummary) -> None:
        if token:
            self._repository.revoke_session(_token_hash(token), datetime.now(UTC))
        self._repository.add_security_event(
            actor_user_id=user.id,
            actor_label=user.actor_label,
            action="Logout realizado",
            target_user_id=user.id,
        )

    def complete_onboarding(self, user: UserSummary) -> UserSummary:
        completed_at = datetime.now(UTC)
        self._repository.mutate(
            user.id,
            lambda target: setattr(target, "onboarding_completed_at", completed_at),
        )
        refreshed = self._repository.get(user.id)
        if refreshed is None:
            raise AuthenticationError("Usuário não encontrado.")
        return _summary(refreshed)

    def list_users(self, actor: UserSummary) -> list[UserSummary]:
        self._require_admin(actor)
        return [_summary(user) for user in self._repository.list_all()]

    def list_active_emails(self, actor: UserSummary) -> list[str]:
        self._require_admin(actor)
        return self._repository.list_active_emails()

    def notification_admin_emails(self) -> list[str]:
        """Uso interno do servidor para alertas restritos, sem expor a lista na UI."""

        return self._repository.list_active_admin_emails()

    def create_user(
        self,
        actor: UserSummary,
        command: UserRegistrationCommand,
    ) -> UserSummary:
        self._require_admin(actor)
        user = self._build_user(command)
        self._repository.add(user)
        created = _summary(user)
        self._repository.add_security_event(
            actor_user_id=actor.id,
            actor_label=actor.actor_label,
            action="Usuário cadastrado",
            target_user_id=created.id,
            details=f"{created.actor_label}; perfil={created.role_label}",
        )
        return created

    def update_user(
        self,
        actor: UserSummary,
        user_id: int,
        command: UserUpdateCommand,
    ) -> UserSummary:
        self._require_admin(actor)
        current = self._repository.get(user_id)
        if current is None:
            raise AuthenticationError(f"Usuário #{user_id} não encontrado.")
        if command.role not in {"admin", "operator", "viewer"}:
            raise AuthenticationError("Perfil de usuário inválido.")
        if user_id == actor.id and not command.is_active:
            raise AuthenticationError("Você não pode desativar a própria conta.")
        removing_last_admin = (
            current.role == "admin"
            and current.is_active
            and (command.role != "admin" or not command.is_active)
            and self._repository.count_active_admins() <= 1
        )
        if removing_last_admin:
            raise AuthenticationError("Mantenha pelo menos um administrador ativo.")
        (
            username,
            normalized_username,
            email,
            normalized_email,
            first_name,
            last_name,
        ) = self._validated_identity(command, excluding_id=user_id)

        def operation(target: UserRecord) -> None:
            target.username = username
            target.normalized_username = normalized_username
            target.email = email
            target.normalized_email = normalized_email
            target.first_name = first_name
            target.last_name = last_name
            target.role = command.role
            target.is_active = command.is_active

        self._repository.mutate(user_id, operation)
        if not command.is_active:
            self._repository.revoke_user_sessions(user_id, datetime.now(UTC))
        refreshed = self._repository.get(user_id)
        if refreshed is None:
            raise AuthenticationError("Usuário não encontrado após a alteração.")
        updated = _summary(refreshed)
        self._repository.add_security_event(
            actor_user_id=actor.id,
            actor_label=actor.actor_label,
            action="Usuário alterado",
            target_user_id=user_id,
            details=(
                f"{updated.actor_label}; perfil={updated.role_label}; ativo={updated.is_active}"
            ),
        )
        return updated

    def reset_password(
        self,
        actor: UserSummary,
        user_id: int,
        password: str,
        confirmation: str,
    ) -> None:
        self._require_admin(actor)
        validated = _validate_password(password, confirmation)
        target = self._repository.get(user_id)
        if target is None:
            raise AuthenticationError(f"Usuário #{user_id} não encontrado.")
        self._repository.mutate(
            user_id,
            lambda record: setattr(record, "password_hash", _hash_password(validated)),
        )
        self._repository.revoke_user_sessions(user_id, datetime.now(UTC))
        self._repository.add_security_event(
            actor_user_id=actor.id,
            actor_label=actor.actor_label,
            action="Senha redefinida pelo administrador",
            target_user_id=user_id,
        )

    def change_own_password(
        self,
        user: UserSummary,
        current_password: str,
        new_password: str,
        confirmation: str,
    ) -> None:
        record = self._repository.get(user.id)
        if record is None or not _verify_password(current_password, record.password_hash):
            raise AuthenticationError("A senha atual está incorreta.")
        validated = _validate_password(new_password, confirmation)
        self._repository.mutate(
            user.id,
            lambda target: setattr(target, "password_hash", _hash_password(validated)),
        )
        self._repository.revoke_user_sessions(user.id, datetime.now(UTC))
        self._repository.add_security_event(
            actor_user_id=user.id,
            actor_label=user.actor_label,
            action="Senha alterada",
            target_user_id=user.id,
        )

    def set_profile_photo(
        self,
        user: UserSummary,
        image_bytes: bytes | None,
    ) -> UserSummary:
        """Salva um avatar otimizado no banco para manter a LAN rápida e o backup completo."""

        encoded: str | None = None
        if image_bytes is not None:
            try:
                optimized = optimize_profile_photo(image_bytes)
            except ProfilePhotoError as error:
                raise AuthenticationError(str(error)) from error
            encoded = base64.b64encode(optimized).decode("ascii")
        self._repository.mutate(
            user.id,
            lambda target: setattr(target, "profile_photo_b64", encoded),
        )
        refreshed = self._repository.get(user.id)
        if refreshed is None:
            raise AuthenticationError("Usuário não encontrado após atualizar a foto.")
        self._repository.add_security_event(
            actor_user_id=user.id,
            actor_label=user.actor_label,
            action="Foto de perfil alterada" if encoded else "Foto de perfil removida",
            target_user_id=user.id,
        )
        return _summary(refreshed)

    @staticmethod
    def _require_admin(user: UserSummary) -> None:
        if not user.is_admin:
            raise AuthenticationError("Somente administradores podem gerenciar usuários.")
