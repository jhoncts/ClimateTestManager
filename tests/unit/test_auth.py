"""Testes de autenticação, perfis, sessões e identificação da auditoria."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.climate_tests import ClimateTestRepository
from climatetest_manager.repositories.users import UserRepository
from climatetest_manager.services.auth import (
    AuthenticationError,
    AuthenticationService,
    UserRegistrationCommand,
    UserUpdateCommand,
)
from climatetest_manager.services.climate_tests import (
    ClimateTestService,
    CreateClimateTestCommand,
)


def registration(
    username: str,
    email: str,
    *,
    role: str = "operator",
) -> UserRegistrationCommand:
    return UserRegistrationCommand(
        username=username,
        email=email,
        first_name="Usuário",
        last_name="de Teste",
        password="Senha123",
        password_confirmation="Senha123",
        role=role,
    )


class AuthenticationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.engine = initialize_database(Path(self.temporary_directory.name) / "auth.db")
        self.session_factory = create_session_factory(self.engine)
        self.user_repository = UserRepository(self.session_factory)
        self.auth = AuthenticationService(self.user_repository)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temporary_directory.cleanup()

    def test_initial_admin_login_session_and_onboarding(self) -> None:
        admin = self.auth.register_initial_admin(registration("jhon.cleiton", "jhon@example.com"))
        self.assertTrue(admin.is_admin)
        stored = self.user_repository.get(admin.id)
        self.assertIsNotNone(stored)
        self.assertNotEqual(stored.password_hash, "Senha123")

        session = self.auth.authenticate(
            "JHON@EXAMPLE.COM",
            "Senha123",
            remember=True,
        )
        restored = self.auth.restore_session(session.token)
        self.assertEqual(restored.id, admin.id)
        self.assertFalse(restored.onboarding_completed)

        completed = self.auth.complete_onboarding(restored)
        self.assertTrue(completed.onboarding_completed)

        self.auth.logout(session.token, completed)
        self.assertIsNone(self.auth.restore_session(session.token))

    def test_admin_manages_users_and_last_admin_is_protected(self) -> None:
        admin = self.auth.register_initial_admin(registration("admin", "admin@example.com"))
        operator = self.auth.create_user(
            admin,
            registration("operador", "operador@example.com"),
        )
        self.assertFalse(operator.is_admin)

        with self.assertRaisesRegex(AuthenticationError, "Somente administradores"):
            self.auth.create_user(
                operator,
                registration("outro", "outro@example.com"),
            )

        with self.assertRaisesRegex(AuthenticationError, "pelo menos um administrador"):
            self.auth.update_user(
                admin,
                admin.id,
                UserUpdateCommand(
                    username=admin.username,
                    email=admin.email,
                    first_name=admin.first_name,
                    last_name=admin.last_name,
                    role="operator",
                    is_active=True,
                ),
            )

    def test_authenticated_actor_is_written_to_test_audit(self) -> None:
        admin = self.auth.register_initial_admin(registration("admin", "admin@example.com"))
        service = ClimateTestService(
            ClimateTestRepository(self.session_factory),
            actor_provider=lambda: admin.actor_label,
        )
        test_id = service.create(
            CreateClimateTestCommand(
                client="Cliente",
                process_number="26123.1",
                product="Luminária",
                epl="Gb",
                tamb_max_c="40",
                delta_t_max_k="35",
                selected_option="B",
            )
        )
        self.assertEqual(service.get_details(test_id).audit_events[0].actor, admin.actor_label)

    def test_duplicate_identity_and_weak_password_are_rejected(self) -> None:
        admin = self.auth.register_initial_admin(registration("admin", "admin@example.com"))
        with self.assertRaisesRegex(AuthenticationError, "usuário já está cadastrado"):
            self.auth.create_user(
                admin,
                registration("ADMIN", "different@example.com"),
            )
        with self.assertRaisesRegex(AuthenticationError, "pelo menos 8"):
            self.auth.create_user(
                admin,
                UserRegistrationCommand(
                    username="novo",
                    email="novo@example.com",
                    first_name="Novo",
                    last_name="Usuário",
                    password="abc1",
                    password_confirmation="abc1",
                ),
            )

    def test_admin_updates_user_resets_password_and_revokes_old_session(self) -> None:
        admin = self.auth.register_initial_admin(registration("admin", "admin@example.com"))
        operator = self.auth.create_user(
            admin,
            registration("operador", "operador@example.com"),
        )
        old_session = self.auth.authenticate(
            operator.username,
            "Senha123",
            remember=True,
        )

        updated = self.auth.update_user(
            admin,
            operator.id,
            UserUpdateCommand(
                username="operador.ensaios",
                email="ensaios@example.com",
                first_name="Operador",
                last_name="Principal",
                role="operator",
                is_active=True,
            ),
        )
        self.assertEqual(updated.username, "operador.ensaios")

        self.auth.reset_password(admin, operator.id, "NovaSenha456", "NovaSenha456")
        self.assertIsNone(self.auth.restore_session(old_session.token))
        new_session = self.auth.authenticate(
            "ensaios@example.com",
            "NovaSenha456",
            remember=False,
        )
        self.assertEqual(new_session.user.id, operator.id)

        with self.assertRaisesRegex(AuthenticationError, "senha atual"):
            self.auth.change_own_password(
                new_session.user,
                "senha-incorreta",
                "OutraSenha789",
                "OutraSenha789",
            )
        self.auth.change_own_password(
            new_session.user,
            "NovaSenha456",
            "OutraSenha789",
            "OutraSenha789",
        )
        authenticated = self.auth.authenticate(
            updated.username,
            "OutraSenha789",
            remember=False,
        )
        self.assertEqual(authenticated.user.id, operator.id)

    def test_profile_photo_is_optional_and_active_emails_are_authorized(self) -> None:
        admin = self.auth.register_initial_admin(registration("admin", "admin@example.com"))
        operator = self.auth.create_user(
            admin,
            registration("operador", "operador@example.com"),
        )
        updated = self.auth.set_profile_photo(
            operator,
            b"\x89PNG\r\n\x1a\nimagem-de-teste",
        )

        self.assertIsNotNone(updated.profile_photo_b64)
        self.assertEqual(
            self.auth.list_active_emails(admin),
            ["admin@example.com", "operador@example.com"],
        )

        without_photo = self.auth.set_profile_photo(updated, None)
        self.assertIsNone(without_photo.profile_photo_b64)

    def test_profile_photo_rejects_invalid_or_oversized_file(self) -> None:
        admin = self.auth.register_initial_admin(registration("admin", "admin@example.com"))

        with self.assertRaisesRegex(AuthenticationError, "PNG, JPG ou WEBP"):
            self.auth.set_profile_photo(admin, b"arquivo invalido")
        with self.assertRaisesRegex(AuthenticationError, "no máximo 2 MB"):
            self.auth.set_profile_photo(admin, b"\x89PNG\r\n\x1a\n" + b"x" * (2 * 1024 * 1024))


if __name__ == "__main__":
    unittest.main()
