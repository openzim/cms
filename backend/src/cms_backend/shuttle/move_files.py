import shutil

from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.book import get_next_book_to_move_files_or_none
from cms_backend.db.models import Book, BookLocation
from cms_backend.shuttle.context import Context as ShuttleContext
from cms_backend.utils.datetime import getnow


def move_files(session: OrmSession):
    nb_zim_files_moved = 0
    while True:
        with session.begin_nested():
            book = get_next_book_to_move_files_or_none(session)
            if not book:
                break

            try:
                logger.info(f"Moving ZIM file(s) of book {book.id}")
                move_book_files(session, book)
                nb_zim_files_moved += 1
            except Exception as exc:
                book.events.append(
                    f"{getnow()}: error encountered while moving file\n{exc}"
                )
                logger.exception(f"Failed to move file for {book.id}")
                book.has_error = True

    if nb_zim_files_moved:
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

    # Grab one valid source file to copy from since it's the same
    # file spread across multiple locations with the same book
    # data
    source_location = current_locations[0]

    current_locations_map = {
        (loc.warehouse_id, loc.path): loc for loc in current_locations
    }

    for target_location in target_locations:
        target_path = target_location.full_local_path(
            ShuttleContext.local_warehouse_paths
        )
        matching_current = current_locations_map.get(
            (target_location.warehouse_id, target_location.path)
        )
        if matching_current:
            # This file is already here. Remove redundant target and remove the current
            # location from the cleanup list
            session.delete(target_location)
            book.locations.remove(target_location)
            current_locations.remove(matching_current)
            logger.debug(f"Left book {book.id} at identical path {target_path}")
            book.events.append(
                f"{getnow()}: left book at identical location "
                f"{target_location.full_str}"
            )
            continue

        source_path = source_location.full_local_path(
            ShuttleContext.local_warehouse_paths
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source_path, target_path)
        logger.debug(f"Copied book {book.id} from {source_path} to {target_path}")
        book.events.append(
            f"{getnow()}: copied book from {source_location.full_str} to "
            f"{target_location.full_str}"
        )
        target_location.status = "current"

        # After making one copy, delete one of the current locations
        # that is not the original to avoid filling disk up with copies
        if len(current_locations) > 1:
            loc_to_delete = current_locations.pop()
            del_path = loc_to_delete.full_local_path(
                ShuttleContext.local_warehouse_paths
            )
            del_path.unlink(missing_ok=True)
            logger.debug(f"Deleted book {book.id} from {del_path}")
            book.events.append(
                f"{getnow()}: deleted book from {loc_to_delete.full_str}"
            )
            book.locations.remove(loc_to_delete)
            session.delete(loc_to_delete)

    # Cleanup the original source location and any extra location (if we
    # started with more currents than targets)
    for current_location in current_locations:
        del_path = current_location.full_local_path(
            ShuttleContext.local_warehouse_paths
        )
        del_path.unlink(missing_ok=True)
        logger.debug(f"Deleted book {book.id} from {del_path}")
        book.events.append(f"{getnow()}: deleted book from {current_location.full_str}")
        book.locations.remove(current_location)
        session.delete(current_location)

    book.needs_file_operation = False
    session.flush()
