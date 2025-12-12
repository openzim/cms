#!/usr/bin/env python3
"""
Development library setup script.

Creates library database records with associated warehouse paths.
"""

import sys
from uuid import UUID

# Add backend source to path for imports
sys.path.insert(0, "/usr/local/lib/python3.13/site-packages")

from cms_backend.db import Session
from cms_backend.db.models import Library, LibraryWarehousePath, WarehousePath


# Configuration: Define libraries and their warehouse paths
# Libraries group warehouse paths together for catalog generation
LIBRARIES_CONFIG = {
    "dev": {
        "id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        # Include dev path from hidden warehouse
        "warehouse_path_names": [("hidden", "dev")],
    },
    "prod": {
        "id": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        # Include all paths from prod warehouse
        "warehouse_path_names": [("prod", "other"), ("prod", "wikipedia")],
    },
    "client1": {
        "id": UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        # Include all paths from client1 warehouse
        "warehouse_path_names": [("client1", "all")],
    },
}


def create_library_structure():
    """Create library database records."""
    session = Session()

    try:
        for library_name, config in LIBRARIES_CONFIG.items():
            print(f"\nProcessing library: {library_name}")
            library_id = config["id"]

            # Check if library already exists
            existing = session.query(Library).filter(Library.id == library_id).first()

            if existing:
                print(f"  ⊘ Library '{library_name}' already exists (skipping)")
                continue

            # Create library DB record with predefined ID
            library = Library(name=library_name)
            library.id = library_id
            session.add(library)
            session.flush()
            print(f"  ✓ Created library '{library_name}' with ID {library.id}")

            # Associate warehouse paths
            for warehouse_name, path_name in config["warehouse_path_names"]:
                # Find the warehouse path by warehouse name and folder name
                warehouse_path = (
                    session.query(WarehousePath)
                    .join(WarehousePath.warehouse)
                    .filter(
                        WarehousePath.folder_name == path_name,
                        WarehousePath.warehouse.has(name=warehouse_name),
                    )
                    .first()
                )

                if not warehouse_path:
                    print(
                        f"    ⚠ Warehouse path '{warehouse_name}/{path_name}' not found "
                        f"(run setup_warehouses.py first)"
                    )
                    continue

                # Create library-warehouse path association
                lwp = LibraryWarehousePath()
                lwp.warehouse_path_id = warehouse_path.id
                library.warehouse_paths.append(lwp)
                session.flush()
                print(
                    f"    ✓ Added path '{warehouse_name}/{path_name}' "
                    f"(ID: {warehouse_path.id})"
                )

        # Commit all changes
        session.commit()
        print("\n✓ All database changes committed")

        # Print summary
        print("\n" + "=" * 70)
        print("Libraries created:")
        print("=" * 70)
        for library_name, config in LIBRARIES_CONFIG.items():
            paths = ", ".join(f"{w}/{p}" for w, p in config["warehouse_path_names"])
            print(f"  {library_name}: {paths}")
            print(f"    Catalog URL: /v1/libraries/{library_name}/catalog.xml")
        print("=" * 70)

    except Exception as e:
        session.rollback()
        print(f"\n✗ Error: {e}", file=sys.stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    create_library_structure()
