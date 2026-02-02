import shutil

from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.book import get_next_book_to_move_files_or_none
from cms_backend.db.models import Book, BookLocation
from cms_backend.shuttle.context import Context as ShuttleContext
from cms_backend.utils.datetime import getnow


def move_files(session: OrmSession):
    logger.info("Moving ZIM files")
    nb_zim_files_moved = 0
    while True:
        with session.begin_nested():
            book = get_next_book_to_move_files_or_none(session)
            if not book:
                break

            try:
                logger.debug(f"Processing ZIM file of book {book.id}")
                move_book_files(session, book)
                nb_zim_files_moved += 1
            except Exception as exc:
                book.events.append(
                    f"{getnow()}: error encountered while moving file\n{exc}"
                )
                logger.exception(f"Failed to move file for {book.id}")
                book.has_error = True

    logger.info(f"Done moving {nb_zim_files_moved} ZIM files")


def move_book_files(session: OrmSession, book: Book):
    inaccessible_warehouse_names = {
        loc.warehouse.name
        for loc in book.locations
        if loc.warehouse_id not in ShuttleContext.local_warehouse_paths.keys()
    }

    # if any warehouse is not accessible, we do not proceed (complex scenarii not yet
    # implemented)
    if len(inaccessible_warehouse_names) > 0:
        logger.debug(
            f"Ignoring book {book.id}, no access to "
            f"{','.join(inaccessible_warehouse_names)} warehouses"
        )
        return

    current_locations: list[BookLocation] = [
        loc for loc in book.locations if loc.status == "current"
    ]

    target_locations: list[BookLocation] = [
        loc for loc in book.locations if loc.status == "target"
    ]

    if len(current_locations) == 0:
        book.events.append(
            f"{getnow()}: error encountered while moving files, no current location"
        )
        book.has_error = True
        return

    if len(target_locations) == 0:
        book.events.append(
            f"{getnow()}: ignoring move files operation, no target location set"
        )
        book.needs_file_operation = False
        return

    # start with copies
    while len(target_locations) > len(current_locations):
        current_location = current_locations[0]
        target_location = target_locations[0]

        current_path = current_location.full_local_path(
            ShuttleContext.local_warehouse_paths
        )
        target_path = target_location.full_local_path(
            ShuttleContext.local_warehouse_paths
        )

        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(current_path, target_path)
        logger.debug(f"Copied book {book.id} from {current_path} to {target_path}")
        book.events.append(
            f"{getnow()}: copied book from {current_location.full_str} to "
            f"{target_location.full_str}"
        )
        target_locations.remove(target_location)
        target_location.status = "current"

    # continue with moves
    while len(current_locations) > 0 and len(target_locations) > 0:
        current_location = current_locations[0]
        target_location = target_locations[0]

        current_path = current_location.full_local_path(
            ShuttleContext.local_warehouse_paths
        )
        target_path = target_location.full_local_path(
            ShuttleContext.local_warehouse_paths
        )

        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(current_path, target_path)
        logger.debug(f"Moved book {book.id} from {current_path} to {target_path}")
        book.events.append(
            f"{getnow()}: moved book from {current_location.full_str} to "
            f"{target_location.full_str}"
        )
        current_locations.remove(current_location)
        target_locations.remove(target_location)
        book.locations.remove(current_location)
        session.delete(current_location)
        session.flush()
        target_location.status = "current"

    # cleanup phase: delete extra current locations
    while len(current_locations) > 0:
        current_location = current_locations[0]
        current_path = current_location.full_local_path(
            ShuttleContext.local_warehouse_paths
        )

        current_path.unlink(missing_ok=True)
        logger.debug(
            f"Deleted extra current location for book {book.id} at {current_path}"
        )
        book.events.append(
            f"{getnow()}: deleted old location {current_location.full_str}"
        )
        current_locations.remove(current_location)
        book.locations.remove(current_location)
        session.delete(current_location)

    book.needs_file_operation = False
