#!/usr/bin/env python3
"""
Development zimfarm notifications setup script.

Creates ZimfarmNotification records for testing the mill processor.
"""

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from cms_backend.db import Session
from cms_backend.db.models import ZimfarmNotification


# Base directory where warehouse folders are located (inside container)
WAREHOUSE_BASE_PATH = Path("/warehouses")

# Small 48x48 PNG icons encoded as base64 (for Illustration_48x48@1 metadata)
# These are minimal valid PNGs with solid colors
FAVICON_BLUE = (
    "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAOklEQVR4nO3OwQkAIAwA"
    "wfRf2u1gB4kfQeYKCHcNAAAAAAAAAAAAgL96bPf7EgAAAAAAAIC/egF5uwED0gQ8ugAAAA"
    "BJRU5ErkJggg=="
)
FAVICON_GREEN = (
    "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAOklEQVR4nO3OwQkAIAwA"
    "wfRf2u1gB4kfQebAoHANAAAAAAAAAAAAgL96bPf7EgAAAAAAAIC/egF5uwEDCgQ8ugAAAA"
    "BJRU5ErkJggg=="
)
FAVICON_RED = (
    "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAOklEQVR4nO3OwQkAIAwA"
    "wfRf2u1gB4kfQeYSCHcNAAAAAAAAAAAAgL96bPf7EgAAAAAAAIC/egF5uwED8gQ8ugAAAA"
    "BJRU5ErkJggg=="
)

# Configuration: Define sample notifications
# Each notification should match a title's producer_unique_id and warehouse path
NOTIFICATIONS_CONFIG = [
    {
        "article_count": 10000,
        "media_count": 5000,
        "size": 1024000000,
        "metadata": {
            "Name": "wikipedia_en_all",
            "Title": "Wikipedia English All Maxi",
            "Creator": "openZIM",
            "Publisher": "Kiwix",
            "Date": "2025-01-15",
            "Description": "Wikipedia English offline",
            "Language": "eng",
            "Flavour": "maxi",
            "Illustration_48x48@1": FAVICON_BLUE,
        },
        "zimcheck": {"status": "pass"},
        "warehouse_name": "hidden",
        "folder_name": "jail",
        "filename": "wikipedia_en_all_maxi_2025-01.zim",
        "producer": {
            "displayName": "farm.openzim.org: wikipedia_en_all_maxi",
            "displayUrl": "https://farm.openzim.org/recipes/wikipedia_en_all_maxi",
            "uniqueId": "farm.openzim.org:wikipedia_en_all_maxi",
        },
    },
    {
        "article_count": 500,
        "media_count": 200,
        "size": 50000000,
        "metadata": {
            "Name": "wiktionary_fr_all",
            "Title": "Wiktionnaire Francais",
            "Creator": "openZIM",
            "Publisher": "Kiwix",
            "Date": "2025-01-10",
            "Description": "Wiktionnaire hors-ligne",
            "Language": "fra",
            "Flavour": "maxi",
            "Illustration_48x48@1": FAVICON_GREEN,
        },
        "zimcheck": {"status": "pass"},
        "warehouse_name": "hidden",
        "folder_name": "jail",
        "filename": "wiktionary_fr_all_maxi_2025-01.zim",
        "producer": {
            "displayName": "wiktionary_fr",
            "displayUrl": "https://farm.openzim.org/recipes/wiktionary_fr",
            "uniqueId": "farm.openzim.org:wiktionary_fr",
        },
    },
    {
        "article_count": 1500,
        "media_count": 2020,
        "size": 40000,
        "metadata": {
            "Name": "wiktionary_en_all",
            "Title": "English Wiktionary",
            "Creator": "openZIM",
            "Publisher": "Kiwix",
            "Date": "2025-01-10",
            "Description": "Offline wiktionary",
            "Language": "eng",
            "Flavour": "maxi",
            "Illustration_48x48@1": FAVICON_RED,
        },
        "zimcheck": {"status": "pass"},
        "warehouse_name": "hidden",
        "folder_name": "jail",
        "filename": "wiktionary_en_all_maxi_2025-01.zim",
        "producer": {
            "displayName": "wiktionary_en",
            "displayUrl": "https://farm.openzim.org/recipes/wiktionary_en",
            "uniqueId": "farm.openzim.org:wiktionary_en",
        },
    },
]


def create_notifications():
    """Create zimfarm notification records and placeholder files."""
    session = Session()

    created_notifications = []

    try:
        for content in NOTIFICATIONS_CONFIG:
            filename = content.get("filename", "unknown")
            warehouse_name = content["warehouse_name"]
            folder_name = content["folder_name"]

            print(f"\nProcessing notification: {filename}")

            # Check if file already exists in warehouse
            file_path = WAREHOUSE_BASE_PATH / warehouse_name / folder_name / filename
            if file_path.exists():
                print(f"  - File already exists at {file_path} (skipping)")
                continue

            # Generate random notification ID
            notification_id = uuid4()

            # Create notification record
            notification = ZimfarmNotification(
                id=notification_id,
                received_at=datetime.now(),
                content=content,
            )
            session.add(notification)
            session.flush()
            print(f"  + Created notification '{filename}' with ID {notification.id}")
            print(f"    Status: {notification.status}")

            # Create placeholder file with notification ID
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(str(notification_id))
            print(f"  + Created file: {file_path}")

            created_notifications.append(
                (filename, warehouse_name, folder_name, notification_id)
            )

        # Commit all changes
        session.commit()
        print("\n+ All database changes committed")

        # Print summary
        if created_notifications:
            print("\n" + "=" * 70)
            print("Notifications created (status: pending):")
            print("=" * 70)
            for (
                filename,
                warehouse_name,
                folder_name,
                notification_id,
            ) in created_notifications:
                print(f"  {filename}")
                print(f"    warehouse: {warehouse_name}/{folder_name}")
                print(f"    id: {notification_id}")
            print("=" * 70)
            print("\nThe mill will now process these notifications into books.")
        else:
            print("\nNo new notifications created (all files already exist).")

    except Exception as e:
        session.rollback()
        print(f"\n- Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    create_notifications()
