"""Mill component - background task processing.

Handles periodic tasks, data processing, and async job execution.
"""

import argparse
import logging
from time import sleep

from cms_backend import logger
from cms_backend.__about__ import __version__
from cms_backend.context import Context
from cms_backend.db import Session
from cms_backend.mill.context import Context as MillContext
from cms_backend.mill.process_zimfarm_notifications import process_zimfarm_notifications
from cms_backend.utils.database import upgrade_db_schema
from cms_backend.utils.datetime import getnow
from cms_backend.utils.task_config import TaskConfig

# Configure background tasks with their execution intervals
tasks: list[TaskConfig] = [
    TaskConfig(
        func=process_zimfarm_notifications,
        interval=MillContext.process_zimfarm_notifications_interval,
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

    logger.info("Mill component starting...")
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
        logger.debug(f"Loop sleeping for {MillContext.pause_in_the_loop}s...")
        sleep(MillContext.pause_in_the_loop)
