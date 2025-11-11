import re
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, BookLocation, Title, WarehousePath
from cms_backend.processors.book import (
    _current_locations_match_targets,  # pyright: ignore[reportPrivateUsage]
    check_book_qa,
    get_matching_title,
)

MINIMUM_ZIM_METADATA = {
    "Name": "test_en_all",
    "Title": "A superb ZIM",
    "Creator": "openZIM",
    "Publisher": "openZIM",
    "Date": "2025-10-01",
    "Description": "About a super content",
    "Language": "eng",
}

# minimum set of metadata + a long description + a flavour + a random one
GOOD_ZIM_METADATA = {
    **MINIMUM_ZIM_METADATA,
    "Long description": "X" * 100,
    "Flavour": "nopic",
    "Foo": "Bar",
}


def test_check_book_qa_ok(create_book: Callable[..., Book]):
    """Check book QA - all is good"""

    book = create_book(zim_metadata=GOOD_ZIM_METADATA)
    assert len(book.events) == 0
    book_qa = check_book_qa(book=book)
    assert book_qa is True
    assert any(
        event for event in book.events if re.match(".*: book passed QA checks", event)
    )


@pytest.mark.parametrize(
    "missing_key, book_metadata",
    [
        pytest.param(
            missing_key,
            {
                key: value
                for key, value in GOOD_ZIM_METADATA.items()
                if key != missing_key
            },
            id=f"missing-{missing_key}",
        )
        for missing_key in MINIMUM_ZIM_METADATA.keys()
    ],
)
def test_check_book_qa_missing_mandatory(
    create_book: Callable[..., Book], missing_key: str, book_metadata: dict[str, Any]
):
    """Check book QA - one mandatory key is missing"""

    book = create_book(zim_metadata=book_metadata)
    assert len(book.events) == 0
    book_qa = check_book_qa(book=book)
    assert book_qa is False
    assert any(
        event
        for event in book.events
        if re.match(f".*: book is missing mandatory metadata: {missing_key}", event)
    )


def test_check_book_qa_missing_multiple_mandatory(create_book: Callable[..., Book]):
    """Check book QA - one mandatory key is missing"""

    book = create_book(
        zim_metadata={
            key: value
            for key, value in GOOD_ZIM_METADATA.items()
            if key not in ("Description", "Title")
        }
    )
    assert len(book.events) == 0
    book_qa = check_book_qa(book=book)
    assert book_qa is False
    assert any(
        event
        for event in book.events
        if re.match(".*: book is missing mandatory metadata: Description,Title", event)
    )


def test_check_book_qa_bad_error(create_book: Callable[..., Book]):
    """Get matching title for a given book - bad error occurs"""

    book = create_book(zim_metadata=GOOD_ZIM_METADATA)
    assert len(book.events) == 0
    # simulate a very bad error by dropping an expected property (and adding it back so
    # that SQLAlchemy does not choke)
    save_metadata = book.zim_metadata
    del book.zim_metadata
    book_qa = check_book_qa(book=book)
    book.zim_metadata = save_metadata
    assert book_qa is False
    assert any(
        event
        for event in book.events
        if re.match(".*: error encountered while checking book QA", event)
    )


def test_get_matching_title_found(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Get matching title for a given book - title exist"""

    book = create_book(name=title.name, producer_unique_id=title.producer_unique_id)
    assert len(book.events) == 0
    assert len(title.events) == 0
    matching_title = get_matching_title(dbsession, book=book)
    assert matching_title == title
    assert any(
        event for event in book.events if re.match(".*: found matching title .*", event)
    )
    assert len(title.events) == 0


def test_get_matching_title_not_found(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Get matching title for a given book - title does not exist"""

    book_name = "test2_fr_all"
    assert book_name != title.name
    book = create_book(name=book_name)
    assert len(book.events) == 0
    assert len(title.events) == 0
    matching_title = get_matching_title(dbsession, book=book)
    assert matching_title is None
    assert any(
        event
        for event in book.events
        if re.match(".*: no matching title found for book", event)
    )
    assert len(title.events) == 0


def test_get_matching_title_no_name(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Get matching title for a given book - book has an empty Name"""

    book_name = ""
    assert book_name != title.name
    book = create_book(name=book_name)
    assert len(book.events) == 0
    assert len(title.events) == 0
    matching_title = get_matching_title(dbsession, book=book)
    assert matching_title is None
    assert any(
        event
        for event in book.events
        if re.match(".*: no title can be found because name is missing", event)
    )
    assert len(title.events) == 0


def test_get_matching_title_bad_error(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Get matching title for a given book - bad error occurs"""

    book = create_book(name=title.name)
    assert len(book.events) == 0
    assert len(title.events) == 0
    # simulate a very bad error by dropping an expected property (and adding it back so
    # that SQLAlchemy does not choke)
    save_producer_unique_id = book.producer_unique_id
    del book.producer_unique_id
    matching_title = get_matching_title(dbsession, book=book)
    book.producer_unique_id = save_producer_unique_id
    assert matching_title is None
    assert any(
        event
        for event in book.events
        if re.match(".*: error encountered while get matching title", event)
    )
    assert len(title.events) == 0


class TestCurrentLocationsMatchTargets:
    """Test the _current_locations_match_targets helper function."""

    def test_exact_match_single_location(
        self,
        dbsession: OrmSession,
        create_book: Callable[..., Book],
        create_warehouse_path: Callable[..., WarehousePath],
    ):
        """Book with single current location matching single target should return
        True."""
        book = create_book()
        warehouse_path = create_warehouse_path()

        # Add current location
        current_location = BookLocation(
            book_id=book.id,
            status="current",
            filename="test_book_2024-01.zim",
        )
        current_location.warehouse_path_id = warehouse_path.id
        book.locations.append(current_location)
        dbsession.add(current_location)
        dbsession.flush()

        # Target matches current
        target_locations = [(warehouse_path.id, "test_book_2024-01.zim")]

        assert _current_locations_match_targets(book, target_locations) is True

    def test_exact_match_multiple_locations(
        self,
        dbsession: OrmSession,
        create_book: Callable[..., Book],
        create_warehouse_path: Callable[..., WarehousePath],
    ):
        """Book with multiple locations matching all targets should return True."""
        book = create_book()
        path1 = create_warehouse_path(folder_name="path1")
        path2 = create_warehouse_path(folder_name="path2")

        # Add current locations
        loc1 = BookLocation(
            book_id=book.id,
            status="current",
            filename="test_book_2024-01.zim",
        )
        loc1.warehouse_path_id = path1.id
        loc2 = BookLocation(
            book_id=book.id,
            status="current",
            filename="test_book_2024-01.zim",
        )
        loc2.warehouse_path_id = path2.id
        book.locations.extend([loc1, loc2])
        dbsession.add(loc1)
        dbsession.add(loc2)
        dbsession.flush()

        # Targets match all currents
        target_locations = [
            (path1.id, "test_book_2024-01.zim"),
            (path2.id, "test_book_2024-01.zim"),
        ]

        assert _current_locations_match_targets(book, target_locations) is True

    def test_no_match_different_filenames(
        self,
        dbsession: OrmSession,
        create_book: Callable[..., Book],
        create_warehouse_path: Callable[..., WarehousePath],
    ):
        """Book with different filename than target should return False."""
        book = create_book()
        warehouse_path = create_warehouse_path()

        # Add current location with different filename
        current_location = BookLocation(
            book_id=book.id,
            status="current",
            filename="old_filename_2024-01.zim",
        )
        current_location.warehouse_path_id = warehouse_path.id
        book.locations.append(current_location)
        dbsession.add(current_location)
        dbsession.flush()

        # Target has different filename
        target_locations = [(warehouse_path.id, "test_book_2024-01.zim")]

        assert _current_locations_match_targets(book, target_locations) is False

    def test_no_match_different_warehouse_path(
        self,
        dbsession: OrmSession,
        create_book: Callable[..., Book],
        create_warehouse_path: Callable[..., WarehousePath],
    ):
        """Book at different warehouse than target should return False."""
        book = create_book()
        path1 = create_warehouse_path(folder_name="path1")
        path2 = create_warehouse_path(folder_name="path2")

        # Add current location at path1
        current_location = BookLocation(
            book_id=book.id,
            status="current",
            filename="test_book_2024-01.zim",
        )
        current_location.warehouse_path_id = path1.id
        book.locations.append(current_location)
        dbsession.add(current_location)
        dbsession.flush()

        # Target specifies path2
        target_locations = [(path2.id, "test_book_2024-01.zim")]

        assert _current_locations_match_targets(book, target_locations) is False

    def test_no_match_subset_current_locations(
        self,
        dbsession: OrmSession,
        create_book: Callable[..., Book],
        create_warehouse_path: Callable[..., WarehousePath],
    ):
        """Book with only 1 current location should not match 2 target locations."""
        book = create_book()
        path1 = create_warehouse_path(folder_name="path1")
        path2 = create_warehouse_path(folder_name="path2")

        # Add current location at only path1
        current_location = BookLocation(
            book_id=book.id,
            status="current",
            filename="test_book_2024-01.zim",
        )
        current_location.warehouse_path_id = path1.id
        book.locations.append(current_location)
        dbsession.add(current_location)
        dbsession.flush()

        # Targets specify both paths
        target_locations = [
            (path1.id, "test_book_2024-01.zim"),
            (path2.id, "test_book_2024-01.zim"),
        ]

        assert _current_locations_match_targets(book, target_locations) is False

    def test_no_match_superset_current_locations(
        self,
        dbsession: OrmSession,
        create_book: Callable[..., Book],
        create_warehouse_path: Callable[..., WarehousePath],
    ):
        """Book with more current locations than targets should return False."""
        book = create_book()
        path1 = create_warehouse_path(folder_name="path1")
        path2 = create_warehouse_path(folder_name="path2")

        # Add current locations at both paths
        loc1 = BookLocation(
            book_id=book.id,
            status="current",
            filename="test_book_2024-01.zim",
        )
        loc1.warehouse_path_id = path1.id
        loc2 = BookLocation(
            book_id=book.id,
            status="current",
            filename="test_book_2024-01.zim",
        )
        loc2.warehouse_path_id = path2.id
        book.locations.extend([loc1, loc2])
        dbsession.add(loc1)
        dbsession.add(loc2)
        dbsession.flush()

        # Targets specify only one path
        target_locations = [(path1.id, "test_book_2024-01.zim")]

        assert _current_locations_match_targets(book, target_locations) is False

    def test_no_match_empty_current_locations(
        self,
        dbsession: OrmSession,
        create_book: Callable[..., Book],
        create_warehouse_path: Callable[..., WarehousePath],
    ):
        """Book with no current locations should not match non-empty targets."""
        book = create_book()
        warehouse_path = create_warehouse_path()

        # Book has no locations
        dbsession.flush()

        # Targets specify locations
        target_locations = [(warehouse_path.id, "test_book_2024-01.zim")]

        assert _current_locations_match_targets(book, target_locations) is False

    def test_ignores_target_status_locations(
        self,
        dbsession: OrmSession,
        create_book: Callable[..., Book],
        create_warehouse_path: Callable[..., WarehousePath],
    ):
        """Helper should ignore target status locations and only check current."""
        book = create_book()
        warehouse_path = create_warehouse_path()

        # Add only target location (no current locations)
        target_location = BookLocation(
            book_id=book.id,
            status="target",
            filename="test_book_2024-01.zim",
        )
        target_location.warehouse_path_id = warehouse_path.id
        book.locations.append(target_location)
        dbsession.add(target_location)
        dbsession.flush()

        # Targets specify locations
        target_locations = [(warehouse_path.id, "test_book_2024-01.zim")]

        # Should return False because there are no current locations
        assert _current_locations_match_targets(book, target_locations) is False
