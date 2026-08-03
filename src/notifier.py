"""Ponto de entrada silencioso do verificador de notificações do Windows."""

import argparse
import os
from contextlib import suppress

from climatetest_manager.config import get_database_path, load_email_settings
from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.climate_tests import ClimateTestRepository
from climatetest_manager.repositories.users import UserRepository
from climatetest_manager.services.exports import create_configured_database_backups
from climatetest_manager.services.notifications import (
    EmailNotificationProvider,
    WindowsToastProvider,
    deliver_due_notifications,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--data-directory", default="")
    return parser.parse_args()


def main() -> None:
    arguments = _arguments()
    if arguments.data_directory:
        os.environ["CLIMATETEST_DATA_DIR"] = arguments.data_directory
    with suppress(OSError, ValueError):
        create_configured_database_backups(get_database_path())
    engine = initialize_database()
    try:
        session_factory = create_session_factory(engine)
        repository = ClimateTestRepository(session_factory)
        user_repository = UserRepository(session_factory)
        email_settings = load_email_settings()
        email_provider = (
            EmailNotificationProvider(
                email_settings,
                user_repository.list_active_emails(),
            )
            if email_settings.is_configured
            else None
        )
        deliver_due_notifications(
            repository,
            WindowsToastProvider(),
            email_provider=email_provider,
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
