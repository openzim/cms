#!/usr/bin/env python3
"""
Development titles setup script.

Creates Title records and associates them with warehouse paths.
"""

from cms_backend.db import Session
from cms_backend.db.models import Title, TitleWarehousePath, Warehouse, WarehousePath

# Configuration: Define titles and their warehouse path associations
# Format for paths: (warehouse_name, folder_name)
TITLES_CONFIG = [
    {
        "name": "wikipedia_en_all",
        "producer_unique_id": "farm.openzim.org:wikipedia_en_all_maxi",
        "dev_paths": [("hidden", "dev")],
        "prod_paths": [("prod", "other")],
    },
    {
        "name": "wiktionary_fr_all",
        "producer_unique_id": "farm.openzim.org:wiktionary_fr",
        "producer_display_name": "wiktionary_fr",
        "producer_display_url": "https://farm.openzim.org/recipes/wiktionary_fr",
        "in_prod": True,
        "dev_paths": [("hidden", "dev")],
        "prod_paths": [("prod", "other"), ("client1", "all")],
    },
]


def get_warehouse_path(session, warehouse_name: str, folder_name: str) -> WarehousePath:
    """Look up a WarehousePath by warehouse name and folder name."""
    result = (
        session.query(WarehousePath)
        .join(Warehouse)
        .filter(
            Warehouse.name == warehouse_name,
            WarehousePath.folder_name == folder_name,
        )
        .first()
    )
    if not result:
        raise ValueError(
            f"WarehousePath not found: {warehouse_name}/{folder_name}. "
            "Run setup_warehouses.py first."
        )
    return result


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
                producer_unique_id=title_config["producer_unique_id"],
            )
            # Set optional fields
            if "in_prod" in title_config:
                title.in_prod = title_config["in_prod"]
            if "producer_display_name" in title_config:
                title.producer_display_name = title_config["producer_display_name"]
            if "producer_display_url" in title_config:
                title.producer_display_url = title_config["producer_display_url"]

            session.add(title)
            session.flush()  # Get the generated UUID
            print(f"  + Created title '{title_name}' with ID {title.id}")

            # Associate dev warehouse paths
            for warehouse_name, folder_name in title_config.get("dev_paths", []):
                warehouse_path = get_warehouse_path(
                    session, warehouse_name, folder_name
                )
                twp = TitleWarehousePath(path_type="dev")
                twp.title = title
                twp.warehouse_path = warehouse_path
                session.add(twp)
                print(f"    + Added dev path: {warehouse_name}/{folder_name}")

            # Associate prod warehouse paths
            for warehouse_name, folder_name in title_config.get("prod_paths", []):
                warehouse_path = get_warehouse_path(
                    session, warehouse_name, folder_name
                )
                twp = TitleWarehousePath(path_type="prod")
                twp.title = title
                twp.warehouse_path = warehouse_path
                session.add(twp)
                print(f"    + Added prod path: {warehouse_name}/{folder_name}")

        # Commit all changes
        session.commit()
        print("\n+ All database changes committed")

        # Print summary
        print("\n" + "=" * 70)
        print("Titles configured:")
        print("=" * 70)
        for title_config in TITLES_CONFIG:
            dev_paths = ", ".join(
                f"{w}/{f}" for w, f in title_config.get("dev_paths", [])
            )
            prod_paths = ", ".join(
                f"{w}/{f}" for w, f in title_config.get("prod_paths", [])
            )
            print(f"  {title_config['name']}")
            if (in_prod := title_config.get("in_prod")) is not None:
                print(f"    in_prod:  {in_prod}")
            print(f"    dev:  {dev_paths or '(none)'}")
            print(f"    prod: {prod_paths or '(none)'}")
        print("=" * 70)

    except Exception as e:
        session.rollback()
        print(f"\n- Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    create_titles()
