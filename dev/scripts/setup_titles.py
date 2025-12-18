#!/usr/bin/env python3
"""
Development titles setup script.

Creates Title records and associates them with collection paths.
"""

from cms_backend.db import Session
from cms_backend.db.models import Title, CollectionTitle

# Configuration: Define titles and their collection path associations
TITLES_CONFIG = [
    {
        "name": "wikipedia_en_all",
        "maturity": "dev",
        "collections": [
            {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "path": "wikipedia"}
        ],
    },
    {
        "name": "wiktionary_fr_all",
        "maturity": "robust",
        "collections": [
            {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "path": "other"},
            {"id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "path": "all"},
        ],
    },
]


def create_titles():
    """Create title records and associate them with warehouse paths."""
    session = Session()

    try:
        for title_config in TITLES_CONFIG:
            title_name = title_config["name"]
            print(f"\nProcessing title: {title_name}")

            # Check if title already exists
            existing = session.query(Title).filter(Title.name == title_name).first()

            if existing:
                print(f"  - Title '{title_name}' already exists (skipping)")
                continue

            # Create title record
            title = Title(
                name=title_name,
            )
            # Set optional fields
            if "maturity" in title_config:
                title.maturity = title_config["maturity"]

            session.add(title)
            session.flush()  # Get the generated UUID
            print(f"  + Created title '{title_name}' with ID {title.id}")

            # Associate collections
            for collection in title_config.get("collections", []):
                ct = CollectionTitle(path=collection["path"])
                ct.title = title
                ct.collection_id = collection["id"]
                session.add(ct)
                print(
                    f"    + Added collection: {collection['id']}/{collection['path']}"
                )

        # Commit all changes
        session.commit()
        print("\n+ All database changes committed")

        # Print summary
        print("\n" + "=" * 70)
        print("Titles configured:")
        print("=" * 70)
        for title_config in TITLES_CONFIG:
            print(f"  {title_config['name']}")
            if (maturity := title_config.get("maturity")) is not None:
                print(f"    maturity:  {maturity}")
            for collection in title_config.get("collections", []):
                print(f"    - {collection['id']}/{collection['path']}")
        print("=" * 70)

    except Exception as e:
        session.rollback()
        print(f"\n- Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    create_titles()
