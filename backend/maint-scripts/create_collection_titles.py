#!/usr/bin/env python3
"""Maintenance script to create collection titles for Kiwix folders.

This script:
- Creates titles for a list of folders (named "foo_{folder_name}")
- Associates them with the "Kiwix" collection
- Sets the path to the corresponding folder
- Is idempotent (can be run multiple times without creating duplicates)

Environment variables required:
- DATABASE_URL: PostgreSQL connection string
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker

from cms_backend import logger
from cms_backend.context import get_mandatory_env
from cms_backend.db import cms_dumps, cms_loads
from cms_backend.db.models import Collection, CollectionTitle, Title
from cms_backend.utils.datetime import getnow

# List of folders to create titles for
FOLDERS = [
    "devdocs",
    "freecodecamp",
    "gutenberg",
    "ifixit",
    "libretexts",
    "mooc",
    "other",
    "phet",
    "psiram",
    "stack_exchange",
    "ted",
    "videos",
    "vikidia",
    "wikibooks",
    "wikinews",
    "wikiquote",
    "wikisource",
    "wikiversity",
    "wikivoyage",
    "wiktionary",
    "wikipedia",
    "zimit",
]

COLLECTION_NAME = "Kiwix"


class Context:
    """Class holding every contextual / configuration bits which can be moved"""

    database_url: str = get_mandatory_env("DATABASE_URL")


def get_or_create_kiwix_collection(session: OrmSession) -> Collection:
    """Get existing Kiwix collection or create a new one."""
    collection = session.scalars(
        select(Collection).where(Collection.name == COLLECTION_NAME)
    ).first()

    if not collection:
        raise Exception(f"Impossible to find collection '{COLLECTION_NAME}'")
    else:
        logger.info(f"Using existing collection '{COLLECTION_NAME}' ({collection.id})")

    session.flush()
    return collection


def create_title_for_folder(
    session: OrmSession, folder_name: str, collection: Collection
) -> None:
    """Create a title for a folder and associate it with the collection."""
    title_name = f"foo_{folder_name}"

    # Check if title already exists
    existing_title = session.scalars(
        select(Title).where(Title.name == title_name)
    ).first()

    if existing_title:
        logger.info(f"Title '{title_name}' already exists")
        title = existing_title
    else:
        # Create new title
        title = Title(name=title_name)
        title.events.append(f"{getnow()}: maintenance script: title created")
        session.add(title)
        session.flush()
        logger.info(f"Created title '{title_name}'")

    # Check if collection association already exists
    existing_ct = session.scalars(
        select(CollectionTitle).where(
            CollectionTitle.title_id == title.id,
            CollectionTitle.collection_id == collection.id,
        )
    ).first()

    if existing_ct:
        logger.info(
            f"Title '{title_name}' already associated with collection "
            f"'{collection.name}'"
        )
    else:
        # Create the collection-title association
        collection_title = CollectionTitle(
            path=Path(folder_name),
        )
        collection_title.collection = collection
        collection_title.title = title
        session.add(collection_title)
        title.events.append(
            f"{getnow()}: maintenance script: associated with "
            f"collection '{collection.name}' at path {folder_name}"
        )
        logger.info(
            f"Associated title '{title_name}' with collection "
            f"'{collection.name}' at path {folder_name}"
        )

    session.flush()


def main():
    ctx = Context()

    db_session = sessionmaker(
        bind=create_engine(
            ctx.database_url,
            echo=False,
            json_serializer=cms_dumps,
            json_deserializer=cms_loads,
        )
    )

    with db_session.begin() as session:
        try:
            # Get or create the Kiwix collection
            collection = get_or_create_kiwix_collection(session)

            # Create titles for each folder
            for folder_name in FOLDERS:
                try:
                    create_title_for_folder(session, folder_name, collection)
                except Exception:
                    logger.exception(f"Error creating title for folder '{folder_name}'")

            session.commit()
            logger.info("Successfully completed creating collection titles")

        except Exception:
            logger.exception("Error during collection title creation")
            sys.exit(1)


if __name__ == "__main__":
    main()
