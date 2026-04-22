#!/usr/bin/env python3
"""Maintenance script to create collection titles for existing folders.

This script:
- Creates titles for a list of folders (named "foo_{folder_name}")
- Associates them with their collection
- Sets the path to the corresponding folder
- Is idempotent (can be run multiple times without creating duplicates)

Environment variables required:
- DATABASE_URL: PostgreSQL connection string
"""

from __future__ import annotations

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
FOLDERS = {
    "Kiwix": [
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
    ],
    "Endless": ["endless"],
    "Bard": ["bard"],
    "BSF": ["bsf"],
    "Branded Apps": ["custom_apps"],
}


class Context:
    """Class holding every contextual / configuration bits which can be moved"""

    database_url: str = get_mandatory_env("DATABASE_URL")


def get_collection_by_name(session: OrmSession, collection_name: str) -> Collection:
    """Get existing collection by name."""
    collection = session.scalars(
        select(Collection).where(Collection.name == collection_name)
    ).first()

    if not collection:
        raise Exception(f"Impossible to find collection '{collection_name}'")
    else:
        logger.info(f"Using existing collection '{collection_name}' ({collection.id})")

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

    for collection_name, folders in FOLDERS.items():
        with db_session.begin() as session:
            try:
                # Get or create the Kiwix collection
                collection = get_collection_by_name(session, collection_name)

                # Create titles for each folder
                for folder_name in folders:
                    try:
                        create_title_for_folder(session, folder_name, collection)
                    except Exception:
                        logger.exception(
                            f"Error creating title for folder '{folder_name}'"
                        )

                session.commit()
                logger.info(
                    f"Successfully created '{collection_name}' collection titles"
                )

            except Exception:
                logger.exception(
                    f"Error during '{collection_name}' collection title creation"
                )


if __name__ == "__main__":
    main()
