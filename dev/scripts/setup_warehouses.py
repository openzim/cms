#!/usr/bin/env python3
"""
Development warehouse setup script.

Creates warehouse directories and database records.
"""

import sys
from pathlib import Path
from uuid import UUID

# Add backend source to path for imports
sys.path.insert(0, "/usr/local/lib/python3.13/site-packages")

from cms_backend.db import Session
from cms_backend.db.models import Warehouse


# Configuration: Define warehouses and their paths
# UUIDs must match those in docker-compose.yml LOCAL_WAREHOUSE_PATHS
WAREHOUSES_CONFIG = {
    "hidden": {
        "id": UUID("11111111-1111-1111-1111-111111111111"),
        "paths": ["jail", "staging"],
    },
    "prod": {
        "id": UUID("22222222-2222-2222-2222-222222222222"),
        "paths": ["other", "wikipedia"],
    },
    "client1": {
        "id": UUID("33333333-3333-3333-3333-333333333333"),
        "paths": ["all"],
    },
}

# Base directory where warehouse folders will be created (inside container)
WAREHOUSE_BASE_PATH = Path("/warehouses")


def create_warehouse_structure():
    """Create warehouse directories and database records."""
    session = Session()

    try:
        for warehouse_name, config in WAREHOUSES_CONFIG.items():
            print(f"\nProcessing warehouse: {warehouse_name}")
            warehouse_id = config["id"]

            # Check if warehouse already exists
            existing = (
                session.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
            )

            if existing:
                print(f"  ⊘ Warehouse '{warehouse_name}' already exists (skipping)")
                warehouse = existing
            else:
                # Create warehouse DB record with predefined ID
                warehouse = Warehouse(
                    name=warehouse_name,
                )
                warehouse.id = warehouse_id
                session.add(warehouse)
                session.flush()
                print(
                    f"  ✓ Created warehouse '{warehouse_name}' with ID {warehouse.id}"
                )

            # Create paths for this warehouse
            for path_name in config["paths"]:
                # Create physical directory
                physical_path = WAREHOUSE_BASE_PATH / warehouse_name / path_name
                if physical_path.exists():
                    print(f"    ⊘ Directory already exists: {physical_path}")
                else:
                    physical_path.mkdir(parents=True, exist_ok=True)
                    print(f"    ✓ Created directory: {physical_path}")

                # (no action needed - IDs are predefined in config)

        # Commit all changes
        session.commit()
        print("\n✓ All database changes committed")

        # Print configuration summary
        print("\n" + "=" * 70)
        print("LOCAL_WAREHOUSE_PATHS configuration (already in docker-compose.yml):")
        print("=" * 70)
        env_parts = []
        for warehouse_name, config in WAREHOUSES_CONFIG.items():
            warehouse_base = WAREHOUSE_BASE_PATH / warehouse_name
            env_parts.append(f"{config['id']}:{warehouse_base}")
        env_value = ",".join(env_parts)
        print(f"  {env_value}")
        print("\n" + "=" * 70)

    except Exception as e:
        session.rollback()
        print(f"\n✗ Error: {e}", file=sys.stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    create_warehouse_structure()
