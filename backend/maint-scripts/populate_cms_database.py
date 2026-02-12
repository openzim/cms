#!/usr/bin/env python3
"""Maintenance script to populate CMS database with existing ZIM books.

This script:
- Explores all warehouses for ZIM files
- Creates missing titles and associates them with their collection
- Creates missing books and associates them with their title
- Is idempotent (can be run multiple times without creating duplicates)
- Requires python-libzim to read ZIM metadata
- Populates title and book events with maintenance script attribution

Environment variables required:
- DATABASE_URL: PostgreSQL connection string
- LOCAL_WAREHOUSE_PATHS: Comma-separated list of warehouse_id:path pairs
- QUARANTINE_WAREHOUSE_ID: UUID of quarantine warehouse
- QUARANTINE_BASE_PATH: Base path for quarantine
- STAGING_WAREHOUSE_ID: UUID of staging warehouse
- STAGING_BASE_PATH: Base path for staging warehouse
"""

from __future__ import annotations

import base64
import io
import os
import pathlib
import sys
from pathlib import Path
from typing import Any, NamedTuple
from uuid import UUID, uuid4

from libzim.reader import Archive  # pyright: ignore[reportMissingModuleSource]
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker

from cms_backend import logger
from cms_backend.context import get_mandatory_env
from cms_backend.db import cms_dumps, cms_loads
from cms_backend.db.models import Book, BookLocation, Collection, CollectionTitle, Title
from cms_backend.db.title import get_title_by_name_or_none
from cms_backend.utils.datetime import getnow
from cms_backend.utils.zim import get_missing_metadata_keys


def get_zim_info(fpath: pathlib.Path) -> dict[str, Any]:
    zim = Archive(fpath)
    payload: dict[str, Any] = {
        "id": str(zim.uuid),
        "counter": counters(zim),
        "article_count": zim.article_count,
        "media_count": zim.media_count,
        "size": fpath.stat().st_size,
        "metadata": {
            key: get_text_metadata(zim, key)
            for key in zim.metadata_keys
            if not key.startswith("Illustration_")
        },
    }
    for size in zim.get_illustration_sizes():
        payload["metadata"].update(
            {
                f"Illustration_{size}x{size}": base64.standard_b64encode(
                    zim.get_illustration_item(size).content
                ).decode("ASCII")
            }
        )
    return payload


class MimetypeAndCounter(NamedTuple):
    mimetype: str
    value: int


CounterMap = dict[str, int]


def get_text_metadata(zim: Archive, name: str) -> str:
    """Decoded value of a text metadata"""
    return zim.get_metadata(name).decode("UTF-8")


def getline(src: io.StringIO, delim: str | None = None) -> tuple[bool, str]:
    """C++ stdlib getline() ~clone

    Reads `src` until it finds `delim`.
    returns whether src is EOF and the extracted string (delim excluded)"""
    output = ""
    if not delim:
        return True, src.read()

    char = src.read(1)
    while char:
        if char == delim:
            break
        output += char
        char = src.read(1)
    return char == "", output


def counters(zim: Archive) -> dict[str, int]:
    try:
        return parse_mimetype_counter(get_text_metadata(zim, "Counter"))
    except RuntimeError:  # pragma: no cover (no ZIM avail to test itl)
        return {}  # pragma: no cover


def read_full_mimetype_and_counter_string(
    src: io.StringIO,
) -> tuple[bool, str]:
    """read a single mimetype-and-counter string from source

    Returns whether the source is EOF and the extracted string (or empty one)"""
    params = ""
    eof, mtc_str = getline(src, ";")  # pyright: ignore
    if mtc_str.find("=") == -1:
        while params.count("=") != 2:  # noqa: PLR2004
            eof, params = getline(src, ";")  # pyright: ignore
            if params.count("=") == 2:  # noqa: PLR2004
                mtc_str += ";" + params
            if eof:
                break
    return eof, mtc_str


def parse_a_single_mimetype_counter(string: str) -> MimetypeAndCounter:
    """MimetypeAndCounter from a single mimetype-and-counter string"""
    k: int = string.rfind("=")
    if k != len(string) - 1:
        mime_type: str = string[:k]
        counter: str = string[k + 1 :]
        try:
            return MimetypeAndCounter(mime_type, int(counter))
        except ValueError:
            pass  # value is not castable to int
    return MimetypeAndCounter("", 0)


def parse_mimetype_counter(
    counter_data: str,
) -> CounterMap:
    """Mapping of MIME types with count for each from ZIM Counter metadata string"""
    counters: CounterMap = {}
    ss = io.StringIO(counter_data)
    eof = False
    while not eof:
        eof, mtc_str = read_full_mimetype_and_counter_string(ss)
        mtc = parse_a_single_mimetype_counter(mtc_str)
        if mtc.mimetype:
            counters.update([mtc])
    ss.close()
    return counters


def parse_warehouse_paths() -> dict[UUID, Path]:
    env_value = os.getenv("LOCAL_WAREHOUSE_PATHS", default="")
    if not env_value:
        return {}
    return {
        UUID(warehouse_id): Path(local_path)
        for item in env_value.split(",")
        if item
        for (warehouse_id, local_path) in [item.split(":", 1)]
    }


class Context:
    """Class holding every contextual / configuration bits which can be moved"""

    database_url: str = get_mandatory_env("DATABASE_URL")

    local_warehouse_paths: dict[UUID, Path] = parse_warehouse_paths()

    quarantine_warehouse_id: UUID = UUID(get_mandatory_env("QUARANTINE_WAREHOUSE_ID"))
    quarantine_base_path: Path = Path(get_mandatory_env("QUARANTINE_BASE_PATH"))
    staging_warehouse_id: UUID = UUID(get_mandatory_env("STAGING_WAREHOUSE_ID"))
    staging_base_path: Path = Path(get_mandatory_env("STAGING_BASE_PATH"))


def find_collections_for_zim(
    session: OrmSession,
    warehouse_id: UUID,
    zim_path_in_warehouse: Path,
) -> list[Collection]:
    """Find the collections that this ZIM belongs to based on its path."""
    collections = session.scalars(
        select(Collection).where(Collection.warehouse_id == warehouse_id)
    ).all()

    zim_dir = zim_path_in_warehouse.parent
    results: list[Collection] = []

    for collection in collections:
        for collection_title in collection.titles:
            if collection_title.path == zim_dir:
                results.append(collection)

    return results


def get_or_create_title(
    session: OrmSession,
    name: str,
    collection: Collection,
    zim_path_in_warehouse: Path,
) -> Title:
    """Get existing title by name or create a new one."""
    title = get_title_by_name_or_none(session, name=name)
    if not title:
        # Create new title
        title = Title(name=name)
        title.events.append(f"{getnow()}: maintenance script: title created")
        session.add(title)

    # Check if collection association exists
    existing_ct = None
    for ct in title.collections:
        if ct.collection_id == collection.id:
            existing_ct = ct
            break

    if not existing_ct:
        # Create the collection-title association
        collection_title = CollectionTitle(path=zim_path_in_warehouse.parent)
        collection_title.collection = collection
        collection_title.title = title
        session.add(collection_title)
        title.events.append(
            f"{getnow()}: maintenance script: associated with "
            f"collection '{collection.name}' at path "
            f"{zim_path_in_warehouse.parent}"
        )
        logger.info(f"Associated title '{name}' with collection '{collection.name}'")

    session.flush()

    return title


def book_exists_at_location(
    session: OrmSession,
    *,
    warehouse_id: UUID,
    path: Path,
    filename: str,
) -> Book | None:
    """Check if a book already exists at a specific location."""
    stmt = (
        select(Book)
        .join(BookLocation)
        .where(
            BookLocation.warehouse_id == warehouse_id,
            BookLocation.path == path,
            BookLocation.filename == filename,
        )
    )
    return session.scalars(stmt).first()


def determine_location_kind(
    ctx: Context,
    *,
    warehouse_id: UUID,
    zim_path_in_warehouse: Path,
) -> str:
    """Determine the location_kind based on warehouse ID and path."""
    if warehouse_id == ctx.quarantine_warehouse_id:
        try:
            zim_path_in_warehouse.parent.relative_to(ctx.quarantine_base_path)
            return "quarantine"
        except ValueError:
            pass

    if warehouse_id == ctx.staging_warehouse_id:
        try:
            zim_path_in_warehouse.parent.relative_to(ctx.staging_base_path)
            return "staging"
        except ValueError:
            pass

    return "prod"


def create_book_from_zim(
    ctx: Context,
    session: OrmSession,
    *,
    warehouse_id: UUID,
    zim_path_in_warehouse: Path,
    title: Title,
    zim_info: dict[str, Any],
) -> Book:
    """Create a book from a ZIM file."""
    zim_metadata = zim_info["metadata"]
    book = Book(
        id=uuid4(),
        created_at=getnow(),
        article_count=zim_info["article_count"],
        media_count=zim_info["media_count"],
        size=zim_info["size"],
        zim_metadata=zim_metadata,
        zimcheck_result={},
        name=zim_metadata.get("Name"),
        date=zim_metadata.get("Date"),
        flavour=zim_metadata.get("Flavour"),
        zimfarm_notification=None,
    )
    book.events.append(
        f"{getnow()}: maintenance script: book created from existing ZIM file"
    )

    book.title = title
    title.books.append(book)
    title.events.append(
        f"{getnow()}: maintenance script: book {book.id} added to title"
    )

    session.add(book)

    # Create book location
    location = BookLocation(
        book_id=book.id,
        warehouse_id=warehouse_id,
        path=zim_path_in_warehouse.parent,
        status="current",
        filename=zim_path_in_warehouse.name,
    )
    session.add(location)
    book.locations.append(location)
    book.events.append(
        f"{getnow()}: maintenance script: added current location: "
        f"{zim_path_in_warehouse}"
    )

    book.location_kind = determine_location_kind(
        ctx,
        warehouse_id=warehouse_id,
        zim_path_in_warehouse=zim_path_in_warehouse,
    )

    logger.info(f"Created book {book.id} for {zim_path_in_warehouse}")

    session.flush()
    return book


def process_zim_file(
    ctx: Context,
    session: OrmSession,
    *,
    warehouse_id: UUID,
    warehouse_path: Path,
    zim_file: Path,
) -> None:
    """Process a single ZIM file"""

    # Calculate relative path within warehouse
    zim_path_in_warehouse = zim_file.relative_to(warehouse_path)

    logger.info(f"Processing: {zim_path_in_warehouse}")

    # Check if book already exists at this location
    if existing_book := book_exists_at_location(
        session,
        warehouse_id=warehouse_id,
        path=zim_path_in_warehouse.parent,
        filename=zim_path_in_warehouse.name,
    ):
        logger.info(
            f"Book already exists for '{zim_path_in_warehouse.name}' at "
            f"{zim_path_in_warehouse.parent} in {warehouse_id=} with ID: "
            f"{existing_book.id}), skipping"
        )
        return

    # Read ZIM metadata to get the title name
    try:
        zim_info = get_zim_info(zim_file)
    except Exception:
        logger.exception(f"encountered exception while reading {zim_file} metadata")
        return

    missing_metadata_keys = get_missing_metadata_keys(zim_info["metadata"])
    if missing_metadata_keys:
        logger.warning(
            f"{zim_file} is missing mandatory metadata: "
            f"{','.join(missing_metadata_keys)}"
        )
        return

    collections = find_collections_for_zim(session, warehouse_id, zim_path_in_warehouse)

    if not collections:
        logger.error(
            f"No collection found for warehouse {warehouse_id}. Skipping "
            f"{zim_path_in_warehouse}..."
        )
        return
    if len(collections) > 1:
        logger.error(
            f"Multiple collections found for warehouse {warehouse_id}. "
            f"Unsure how to handle. Skipping {zim_path_in_warehouse}..."
        )
        return

    title = get_or_create_title(
        session, zim_info["metadata"]["Name"], collections[0], zim_path_in_warehouse
    )

    create_book_from_zim(
        ctx,
        session,
        warehouse_id=warehouse_id,
        zim_path_in_warehouse=zim_path_in_warehouse,
        title=title,
        zim_info=zim_info,
    )


def scan_warehouse(
    ctx: Context,
    session: OrmSession,
    *,
    local_warehouse_id: UUID,
    local_warehouse_path: Path,
) -> None:
    """Scan a warehouse for ZIM files and process them."""
    logger.info(f"Scanning warehouse {local_warehouse_id}:{local_warehouse_path}...")

    if not local_warehouse_path.exists():
        logger.warning(f"Warehouse path does not exist: {local_warehouse_path}")
        return

    zim_files = sorted(local_warehouse_path.rglob("*.zim"))

    logger.info(f"Found {len(zim_files)} ZIM file(s) in {local_warehouse_path}")

    for zim_file in zim_files:
        with session.begin_nested():
            try:
                process_zim_file(
                    ctx,
                    session,
                    warehouse_id=local_warehouse_id,
                    warehouse_path=local_warehouse_path,
                    zim_file=zim_file,
                )
            except Exception:
                logger.exception(f"error processing {zim_file}")


def main():
    ctx = Context()

    if not ctx.local_warehouse_paths:
        logger.error("No warehouse paths configured in LOCAL_WAREHOUSE_PATHS")
        sys.exit(1)

    db_session = sessionmaker(
        bind=create_engine(
            ctx.database_url,
            echo=False,
            json_serializer=cms_dumps,
            json_deserializer=cms_loads,
        )
    )

    with db_session.begin() as session:
        for (
            local_warehouse_id,
            local_warehouse_path,
        ) in ctx.local_warehouse_paths.items():
            try:
                scan_warehouse(
                    ctx,
                    session,
                    local_warehouse_id=local_warehouse_id,
                    local_warehouse_path=local_warehouse_path,
                )
            except Exception:
                logger.exception(
                    "encountered exception scanning local warehouse "
                    f"{local_warehouse_id}:{local_warehouse_path}"
                )
                logger.info("Continuing with next warehouse...")


if __name__ == "__main__":
    main()
