#!/usr/bin/env python3
"""
Development collection setup script.

Creates collection database records.
"""

import sys
from uuid import UUID

# Add backend source to path for imports
sys.path.insert(0, "/usr/local/lib/python3.13/site-packages")

from cms_backend.db import Session
from cms_backend.db.models import Collection


# Configuration: Define collections
COLLECTIONS_CONFIG = {
    "prod": {
        "id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        "warehouse_id": UUID("22222222-2222-2222-2222-222222222222"),
    },
    "client1": {
        "id": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        "warehouse_id": UUID("33333333-3333-3333-3333-333333333333"),
    },
}


def create_collections():
    """Create collection database records."""
    session = Session()

    try:
        for collection_name, config in COLLECTIONS_CONFIG.items():
            print(f"\nProcessing library: {collection_name}")
            collection_id = config["id"]

            # Check if library already exists
            existing = (
                session.query(Collection).filter(Collection.id == collection_id).first()
            )

            if existing:
                print(f"  ⊘ Collection '{collection_name}' already exists (skipping)")
                continue

            # Create library DB record with predefined ID
            collection = Collection(
                name=collection_name, warehouse_id=config["warehouse_id"]
            )
            collection.id = collection_id
            session.add(collection)
            session.flush()
            print(f"  ✓ Created collection '{collection_name}' with ID {collection.id}")

        # Commit all changes
        session.commit()
        print("\n✓ All database changes committed")

        # Print summary
        print("\n" + "=" * 70)
        print("Collections created:")
        print("=" * 70)
        for collection_name, config in COLLECTIONS_CONFIG.items():
            collection_id = config["id"]
            print(f"  {collection_name}: {collection_id}")
            print(f"    Warehouse ID: {config['warehouse_id']}")
            print(f"    Catalog URL: /v1/collections/{collection_name}/catalog.xml")
            print(f"             or: /v1/collections/{collection_id}/catalog.xml")
        print("=" * 70)

    except Exception as e:
        session.rollback()
        print(f"\n✗ Error: {e}", file=sys.stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    create_collections()
