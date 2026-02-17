"""Shuttle component - file transfer and warehouse operations.

Handles moving ZIM files between warehouses and managing book locations.
"""

import argparse
import logging
from time import sleep

from cms_backend import logger
from cms_backend.__about__ import __version__
from cms_backend.context import Context
from cms_backend.db import Session
from cms_backend.shuttle.context import Context as ShuttleContext
from cms_backend.shuttle.delete_files import delete_files
from cms_backend.shuttle.move_files import move_files
from cms_backend.utils.database import upgrade_db_schema
from cms_backend.utils.datetime import getnow
from cms_backend.utils.task_config import TaskConfig

# Configure background tasks with their execution intervals
tasks: list[TaskConfig] = [
    TaskConfig(
        func=move_files,
        interval=ShuttleContext.move_files_interval,
    ),
    TaskConfig(
        func=delete_files,
        interval=ShuttleContext.delete_files_interval,
    ),
]


def main():
    """Main entry point for mill component."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        help="Show version and exit.",
        action="version",
        version="%(prog)s: " + __version__,
    )
    parser.add_argument(
        "--verbose", "-v", help="Show verbose output.", action="store_true"
    )

    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    logger.info("Shuttle component starting...")
    logger.info(f"Found {len(tasks)} tasks to process")

    if Context.alembic_upgrade_head_on_start:
        upgrade_db_schema()

    while True:
        now = getnow()
        for task_config in tasks:
            if task_config.should_run(now):
                try:
                    with Session.begin() as session:
                        logger.debug(f"Executing task: {task_config.task_name}")
                        task_config.execute(session)
                except Exception:
                    logger.exception(
                        f"Unexpected error while executing task: "
                        f"{task_config.task_name}"
                    )
        logger.debug(f"Loop sleeping for {ShuttleContext.pause_in_the_loop}s...")
        sleep(ShuttleContext.pause_in_the_loop)
