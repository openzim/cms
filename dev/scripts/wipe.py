#!/usr/bin/env python3
"""
Development wipe script.

Deletes all dev data from the database and all ZIM files from warehouses.
Run inside the shuttle container:
    docker exec cms_shuttle python /scripts/wipe.py
"""

from pathlib import Path

from sqlalchemy import delete, select
from cms_backend.db import Session
from sqlalchemy.orm import Session as OrmSession
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
DEV_PREFIX = "dev\\_%"


def wipe_database(session: OrmSession):
    """Delete all dev data from the database in the correct order."""
    print("Wiping dev entries in database...")

    # Delete in order respecting foreign key constraints
    # (children before parents)

    # 1. BookLocation (depends on Book and WarehousePath)
    count = session.execute(
        delete(BookLocation).where(BookLocation.filename.like(DEV_PREFIX))
    ).rowcount
    print(f"  - Deleted {count} BookLocation records")

    # 2. ZimfarmNotification (depends on Book)
    count = session.execute(
        delete(ZimfarmNotification).where(
            ZimfarmNotification.content.has_key("filename"),
            ZimfarmNotification.content["filename"].astext.like(DEV_PREFIX),
        )
    ).rowcount
    print(f"  - Deleted {count} ZimfarmNotification records")

    # 3. Book (depends on Title)
    count = session.execute(
        delete(Book).where(Book.name.is_not(None), Book.name.like(DEV_PREFIX))
    ).rowcount
    print(f"  - Deleted {count} Book records")

    # 4. CollectionTitle (depends on Title and Collection)
    count = session.execute(
        delete(CollectionTitle).where(
            CollectionTitle.title_id.in_(
                select(Title.id).where(Title.name.like(DEV_PREFIX))
            )
        )
    ).rowcount
    print(f"  - Deleted {count} CollectionTitle records")

    # 5. Title
    count = session.execute(delete(Title).where(Title.name.like(DEV_PREFIX))).rowcount
    print(f"  - Deleted {count} Title records")

    # 7. Collection (depends on Warehouse)
    count = session.execute(
        delete(Collection).where(Collection.name.like(DEV_PREFIX))
    ).rowcount
    print(f"  - Deleted {count} Collection records")

    # 9. Warehouse
    warehouses = session.scalars(
        select(Warehouse.name).where(Warehouse.name.like(DEV_PREFIX))
    ).all()

    count = session.execute(
        delete(Warehouse).where(Warehouse.name.like(DEV_PREFIX))
    ).rowcount

    print(f"  - Deleted {count} Warehouse records")

    print("\nWiping warehouse files...")

    nb_files_deleted = 0
    for warehouse in warehouses:
        nb_files_deleted += wipe_warehouse_files(warehouse)

    print("\n+ Warehouse files wiped successfully")

    print(f"  - Total files deleted: {nb_files_deleted}")


def wipe_warehouse_files(warehouse: str) -> int:
    warehouse_path = WAREHOUSE_BASE_PATH / Path(warehouse)

    if not warehouse_path.exists():
        print(f"  - Warehouse path {warehouse_path} does not exist")
        return 0

    zim_files = list(warehouse_path.rglob("*.zim"))

    if not zim_files:
        print("  - No ZIM files to delete")
        return 0

    nb_files_deleted = 0

    for file_path in zim_files:
        file_path.unlink()
        nb_files_deleted += 1
        print(f"  - Deleted {file_path}")

    return nb_files_deleted


def wipe():
    """Wipe database and warehouse files."""
    session = Session()

    try:
        wipe_database(session)
        session.commit()
        print("\n+ Database wiped successfully")

    except Exception as e:
        session.rollback()
        print(f"\n- Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    wipe()
