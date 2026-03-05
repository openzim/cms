import argparse
import logging
from time import sleep

from cms_backend import logger
from cms_backend.__about__ import __version__
from cms_backend.context import Context
from cms_backend.mill.context import Context as MillContext
from cms_backend.mill.process_title_modifications import (
    process_title_modifications_from_stream,
)
from cms_backend.utils.database import upgrade_db_schema


def main():
    parser = argparse.ArgumentParser(description="Process Redis stream events")
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

    logger.info("Title modification processor starting...")

    if Context.alembic_upgrade_head_on_start:
        upgrade_db_schema()

    while True:
        try:
            logger.debug("Starting title modification processing cycle")
            process_title_modifications_from_stream()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            break
        except Exception:
            logger.exception("Error in title modification processor, retrying...")
            logger.debug(f"Sleeping {MillContext.pause_in_the_loop}s before retry...")
            sleep(MillContext.pause_in_the_loop)
