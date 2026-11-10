#!/usr/bin/env python3

"""
Update properties of titles matching a set of filters.

Goes through update_title() so every change gets a proper author and is
recorded in the title history, exactly like a manual edit via the UI/API.

EXAMPLES:

1. Move all gutenberg_* titles to the "books" path of the "gutenberg"
   collection:
   ./update_title_properties.py \
       --filters="name=^gutenberg_.*" \
       --values="collection_titles=gutenberg:books" \
       --username=jsmith

2. Move all wikipedia_* titles to be served from two collections at once:
   ./update_title_properties.py \
       --filters="name=^wikipedia_.*" \
       --values="collection_titles=wikipedia:wikis,backup:wikipedia" \
       --username=jsmith

3. Preview the changes without applying them:
   ./update_title_properties.py \
       --filters="name=^gutenberg_.*" \
       --values="collection_titles=gutenberg:books" \
       --username=jsmith \
       --dry-run

Supported filter attributes:
    name (POSIX regex, matched with Postgres' `~` operator)

Supported value attributes:
    collection_titles (comma-separated "collection:path" pairs; replaces the
    full existing list of collections the title belongs to)
"""

import argparse
import sys
from collections.abc import Callable
from typing import Any

from sqlalchemy import select

from cms_backend import logger
from cms_backend.db import Session
from cms_backend.db.account import get_account_by_username
from cms_backend.db.models import Title
from cms_backend.db.title import update_title
from cms_backend.schemas.models import TitleUpdateSchema
from cms_backend.schemas.orms import BaseTitleCollectionSchema


def split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_collection_titles(value: str) -> list[BaseTitleCollectionSchema]:
    collection_titles: list[BaseTitleCollectionSchema] = []
    for item in split_list(value):
        collection_name, separator, path = item.partition(":")
        if not separator or not collection_name or not path:
            raise ValueError(
                f"Invalid collection_titles entry '{item}': expected "
                "format 'collection:path'"
            )
        collection_titles.append(
            BaseTitleCollectionSchema(collection_name=collection_name, path=path)
        )
    return collection_titles


# Mapping of supported filter attributes to a callable building the SQL clause
FILTER_ATTRIBUTES: dict[str, Callable[[str], Any]] = {
    "name": Title.name.op("~"),
}

# Mapping of supported value attributes to a callable converting the raw
# string into the value accepted by TitleUpdateSchema.
UPDATABLE_ATTRIBUTES: dict[str, Callable[[str], Any]] = {
    "collection_titles": parse_collection_titles,
}


def parse_pairs(raw: str) -> dict[str, str]:
    """Parse a pipe-separated list of attribute=value pairs."""
    pairs: dict[str, str] = {}
    for raw_item in raw.split("|"):
        item = raw_item.strip()
        if not item:
            continue
        key, separator, value = item.partition("=")
        if not separator:
            raise ValueError(
                f"Invalid pair '{item}': expected format 'attribute=value'"
            )
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid pair '{item}': empty attribute name")
        pairs[key] = value.strip()
    return pairs


def build_filters(pairs: dict[str, str]) -> list[Any]:
    """Build the list of SQL clauses from the parsed filter pairs."""
    clauses: list[Any] = []
    for key, value in pairs.items():
        if key not in FILTER_ATTRIBUTES:
            raise ValueError(
                f"Unknown filter attribute '{key}'. Supported attributes: "
                f"{', '.join(sorted(FILTER_ATTRIBUTES))}"
            )
        clauses.append(FILTER_ATTRIBUTES[key](value))
    return clauses


def build_updates(pairs: dict[str, str]) -> dict[str, Any]:
    """Build the TitleUpdateSchema kwargs from the parsed value pairs."""
    updates: dict[str, Any] = {}
    for key, value in pairs.items():
        if key not in UPDATABLE_ATTRIBUTES:
            raise ValueError(
                f"Unknown value attribute '{key}'. Supported attributes: "
                f"{', '.join(sorted(UPDATABLE_ATTRIBUTES))}"
            )
        updates[key] = UPDATABLE_ATTRIBUTES[key](value)
    return updates


def main(
    *,
    filters: dict[str, str],
    values: dict[str, str],
    comment: str | None,
    dry_run: bool,
    username: str,
) -> None:
    filter_clauses = build_filters(filters)
    updates = build_updates(values)

    with Session() as session:
        stmt: Any = select(Title).order_by(Title.name)
        for clause in filter_clauses:
            stmt = stmt.where(clause)

        titles = session.scalars(stmt).all()
        author_id = get_account_by_username(session, username=username).id

        logger.info(f"Matched {len(titles)} title(s)")

        nb_updated = 0
        for title in titles:
            if title.archived:
                logger.warning(f"Title '{title.name}' is archived. Skipping.")
                continue

            if dry_run:
                logger.info(f"[dry-run] Would update title '{title.name}'")
                nb_updated += 1
                continue

            try:
                update_title(
                    session,
                    title_identifier=str(title.id),
                    author_id=author_id,
                    accessible_collection_ids=None,
                    payload=TitleUpdateSchema(comment=comment, **updates),
                )
            except Exception:
                logger.exception(f"Failed to update title '{title.name}'")
                session.rollback()
                continue

            session.commit()
            nb_updated += 1
            logger.info(f"Updated title '{title.name}'")

        if dry_run:
            logger.info(f"[dry-run] Would have updated {nb_updated} title(s)")
        else:
            logger.info(f"Updated {nb_updated} title(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Update properties of titles matching a set of filters. Both "
            "filters and values are pipe-separated lists of "
            "'attribute=value' pairs."
        ),
    )

    parser.add_argument(
        "--filters",
        default="",
        help=(
            "Pipe-separated list of 'attribute=value' filters used to select "
            "titles, e.g. 'name=^gutenberg_.*'. When omitted, every "
            "(non-archived) title is targeted."
        ),
    )

    parser.add_argument(
        "--values",
        required=True,
        help=(
            "Pipe-separated list of 'attribute=value' pairs to set on the "
            "matched titles, e.g. 'collection_titles=gutenberg:books'. List "
            "attributes accept comma-separated values."
        ),
    )

    parser.add_argument(
        "--comment",
        default="Updated via update_title_properties",
        help="Comment recorded in the title history entry for each update.",
    )

    parser.add_argument(
        "--username", required=True, help="Username of account applying these updates."
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Do not apply the changes"
    )

    args = parser.parse_args()

    try:
        filters = parse_pairs(args.filters)
        values = parse_pairs(args.values)
        if not filters:
            logger.warning("No filters provided: targeting all non-archived titles.")
        if not values:
            raise ValueError("No values provided: nothing to update.")
        main(
            filters=filters,
            values=values,
            comment=args.comment,
            dry_run=args.dry_run,
            username=args.username,
        )
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(1)

    logger.info("FINISH!")
