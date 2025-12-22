#!/usr/bin/env python3
"""
Development wipe script.

Deletes all data from the database and all ZIM files from warehouses.
Run inside the shuttle container:
    docker exec cms_shuttle python /scripts/wipe.py
"""

from pathlib import Path

from cms_backend.db import Session
from cms_backend.db.models import (
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    Title,
    Warehouse,
    ZimfarmNotification,
)


# Base directory where warehouse folders are located (inside container)
WAREHOUSE_BASE_PATH = Path("/warehouses")


def wipe_database(session):
    """Delete all data from the database in the correct order."""
    print("Wiping database...")

    # Delete in order respecting foreign key constraints
    # (children before parents)

    # 1. BookLocation (depends on Book and WarehousePath)
    count = session.query(BookLocation).delete()
    print(f"  - Deleted {count} BookLocation records")

    # 2. ZimfarmNotification (depends on Book)
    count = session.query(ZimfarmNotification).delete()
    print(f"  - Deleted {count} ZimfarmNotification records")

    # 3. Book (depends on Title)
    count = session.query(Book).delete()
    print(f"  - Deleted {count} Book records")

    # 4. CollectionTitle (depends on Title and Collection)
    count = session.query(CollectionTitle).delete()
    print(f"  - Deleted {count} CollectionTitle records")

    # 5. Title
    count = session.query(Title).delete()
    print(f"  - Deleted {count} Title records")

    # 7. Collection (depends on Warehouse)
    count = session.query(Collection).delete()
    print(f"  - Deleted {count} Collection records")

    # 9. Warehouse
    count = session.query(Warehouse).delete()
    print(f"  - Deleted {count} Warehouse records")


def wipe_warehouse_files():
    """Delete all ZIM files in warehouse directories."""
    print("\nWiping warehouse files...")

    if not WAREHOUSE_BASE_PATH.exists():
        print(f"  - Warehouse path {WAREHOUSE_BASE_PATH} does not exist")
        return

    zim_files = list(WAREHOUSE_BASE_PATH.rglob("*.zim"))

    if not zim_files:
        print("  - No ZIM files to delete")
        return

    for file_path in zim_files:
        file_path.unlink()
        print(f"  - Deleted {file_path}")

    print(f"  - Total files deleted: {len(zim_files)}")


def wipe():
    """Wipe database and warehouse files."""
    session = Session()

    try:
        wipe_database(session)
        session.commit()
        print("\n+ Database wiped successfully")

        wipe_warehouse_files()
        print("\n+ Warehouse files wiped successfully")

    except Exception as e:
        session.rollback()
        print(f"\n- Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    wipe()
