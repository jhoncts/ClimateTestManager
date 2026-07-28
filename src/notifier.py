"""Ponto de entrada silencioso do verificador de notificações do Windows."""

import argparse
import os

from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.climate_tests import ClimateTestRepository
from climatetest_manager.services.notifications import (
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
    engine = initialize_database()
    try:
        repository = ClimateTestRepository(create_session_factory(engine))
        deliver_due_notifications(repository, WindowsToastProvider())
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
