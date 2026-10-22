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
from cms_backend.mill.check_book_transitions import check_book_transitions
from cms_backend.mill.context import Context as MillContext
from cms_backend.mill.delete_uploaded_zims import delete_uploaded_zims
from cms_backend.mill.delete_zimcheck_s3_results import delete_zimcheck_s3_results
from cms_backend.mill.fetch_lb_download_stats import fetch_download_stats
from cms_backend.mill.mark_staging_books_for_deletion import (
    mark_staging_books_for_deletion,
)
from cms_backend.mill.process_retention_rules import process_retention_rules
from cms_backend.mill.process_title_modifications import process_title_modifications
from cms_backend.mill.process_zimfarm_notifications import process_zimfarm_notifications
from cms_backend.mill.update_zimfarm_task_status import update_title_uploads_status
from cms_backend.utils.database import create_mill_account, upgrade_db_schema
from cms_backend.utils.datetime import getnow
from cms_backend.utils.task_config import TaskConfig

# Configure background tasks with their execution intervals
tasks: list[TaskConfig] = [
    TaskConfig(
        func=process_zimfarm_notifications,
        interval=MillContext.process_zimfarm_notifications_interval,
        enabled=MillContext.process_zimfarm_notifications_enabled,
    ),
    TaskConfig(
        func=process_title_modifications,
        interval=MillContext.process_events_interval,
        enabled=MillContext.process_title_modifications_enabled,
    ),
    TaskConfig(
        func=check_book_transitions,
        interval=MillContext.check_book_transitions_interval,
        enabled=MillContext.check_book_transitions_enabled,
    ),
    TaskConfig(
        func=process_retention_rules,
        interval=MillContext.process_retention_rules_interval,
        enabled=MillContext.process_retention_rules_enabled,
    ),
    TaskConfig(
        func=mark_staging_books_for_deletion,
        interval=MillContext.mark_staging_books_for_deletion_interval,
        enabled=MillContext.mark_staging_books_for_deletion_enabled,
    ),
    TaskConfig(
        func=update_title_uploads_status,
        interval=MillContext.update_title_upload_status_interval,
        enabled=MillContext.update_title_uploads_status_enabled,
    ),
    TaskConfig(
        func=delete_uploaded_zims,
        interval=MillContext.delete_uploaded_zims_interval,
        enabled=MillContext.delete_uploaded_zims_enabled,
    ),
    TaskConfig(
        func=delete_zimcheck_s3_results,
        interval=MillContext.delete_zimcheck_files_interval,
        enabled=MillContext.delete_zimcheck_s3_results_enabled,
    ),
    TaskConfig(
        func=fetch_download_stats,
        interval=MillContext.fetch_download_stats_interval,
        enabled=MillContext.fetch_download_stats_enabled,
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
    for task_config in tasks:
        logger.info(
            f"Task {task_config.task_name} is "
            f"{'enabled' if task_config.enabled else 'disabled'}"
        )

    if Context.alembic_upgrade_head_on_start:
        upgrade_db_schema()

    create_mill_account()

    while True:
        now = getnow()
        for task_config in tasks:
            if task_config.should_run(now):
                try:
                    with Session() as session:
                        logger.debug(f"Executing task: {task_config.task_name}")
                        task_config.execute(session)
                except Exception:
                    logger.exception(
                        f"Unexpected error while executing task: "
                        f"{task_config.task_name}"
                    )
        logger.debug(f"Loop sleeping for {MillContext.pause_in_the_loop}s...")
        sleep(MillContext.pause_in_the_loop)
