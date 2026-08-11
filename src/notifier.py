"""Ponto de entrada silencioso do verificador de notificações do Windows."""

import argparse
import os
from contextlib import suppress
from pathlib import Path

from climatetest_manager.config import get_database_path, load_email_settings
from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.climate_tests import ClimateTestRepository
from climatetest_manager.repositories.users import UserRepository
from climatetest_manager.services.exports import create_configured_database_backups
from climatetest_manager.services.notifications import (
    EmailNotificationProvider,
    WindowsToastProvider,
    deliver_due_notifications,
    deliver_pending_incident_emails,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--data-directory", default="")
    parser.add_argument(
        "--channels",
        choices=("both", "email", "desktop"),
        default="both",
    )
    return parser.parse_args()


def main() -> None:
    arguments = _arguments()
    if arguments.data_directory:
        os.environ["CLIMATETEST_DATA_DIR"] = arguments.data_directory
        os.environ.setdefault(
            "CLIMATETEST_STORAGE_CONFIG",
            str(Path(arguments.data_directory) / "storage.json"),
        )
    if arguments.channels != "desktop":
        with suppress(OSError, ValueError):
            create_configured_database_backups(get_database_path())
    engine = initialize_database()
    try:
        session_factory = create_session_factory(engine)
        repository = ClimateTestRepository(session_factory)
        user_repository = UserRepository(session_factory)
        email_settings = load_email_settings()
        use_email = arguments.channels in {"both", "email"}
        use_desktop = arguments.channels in {"both", "desktop"}
        automatic_email = use_email and email_settings.automatic_enabled
        email_provider = (
            EmailNotificationProvider(
                email_settings,
                user_repository.list_active_emails(),
            )
            if automatic_email
            else None
        )
        admin_emails = user_repository.list_active_admin_emails()
        admin_email_provider = (
            EmailNotificationProvider(
                email_settings,
                admin_emails,
            )
            if automatic_email and admin_emails
            else None
        )
        deliver_due_notifications(
            repository,
            WindowsToastProvider() if use_desktop else None,
            email_provider=email_provider,
            require_desktop=True,
            require_email=automatic_email,
        )
        if automatic_email:
            deliver_pending_incident_emails(repository, admin_email_provider)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
