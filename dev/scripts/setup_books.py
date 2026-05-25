#!/usr/bin/env python3
"""
Prod book files setup script.

Creates files for the prod books in the DB at their locations so the shuttle can act on them
"""

import sys
from pathlib import Path

# Add backend source to path for imports
sys.path.insert(0, "/usr/local/lib/python3.13/site-packages")

from sqlalchemy import select
from cms_backend.db import Session
from cms_backend.db.models import Book
from cms_backend.db.book import get_book


# Base directory where warehouse folders will be created (inside container)
WAREHOUSE_BASE_PATH = Path("/warehouses")


def create_book_files():
    """Create files for existing books in the DB"""
    print("\nCreating dummy files for books in DB")
    with Session.begin() as session:
        book_ids = session.scalars(
            select(Book.id).where(Book.location_kind != "deleted")
        ).all()
        for book_id in book_ids:
            book = get_book(session, book_id)
            current_locations = [
                location for location in book.locations if location.status == "current"
            ]
            for location in current_locations:
                physical_path = (
                    WAREHOUSE_BASE_PATH / Path(location.warehouse.name) / location.path
                )
                physical_path.mkdir(parents=True, exist_ok=True)
                dest = physical_path / location.filename
                dest.touch(exist_ok=True)
                print(f"Created file for book {book.name} at {dest}")


if __name__ == "__main__":
    create_book_files()
