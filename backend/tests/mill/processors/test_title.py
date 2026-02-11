"""Tests for title processor functions."""

from collections.abc import Callable
from datetime import timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, BookLocation, Title
from cms_backend.mill.processors.title import (
    apply_retention_rules,
    sort_books_by_filename_period,
)
from cms_backend.utils.datetime import getnow


def test_sort_books_by_filename_period(
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
):
    """Books with mixed periods and suffixes should be sorted correctly."""
    book1 = create_book()
    create_book_location(book=book1, filename="wiki_2024-01.zim")

    book2 = create_book()
    create_book_location(book=book2, filename="wiki_2024-01a.zim")

    book3 = create_book()
    create_book_location(book=book3, filename="wiki_2024-02.zim")

    book4 = create_book()
    create_book_location(book=book4, filename="wiki_2023-12z.zim")

    book5 = create_book()
    create_book_location(book=book5, filename="wiki_2023-12aa.zim")

    book6 = create_book()
    create_book_location(book=book6, filename="wiki_2024-01aa.zim")

    book7 = create_book()
    create_book_location(book=book7, filename="wiki_2024-01b.zim")

    book8 = create_book()
    create_book_location(book=book8, filename="wiki_2024-01ba.zim")

    book9 = create_book()
    create_book_location(book=book9, filename="wiki_2024-02a.zim")

    result = sort_books_by_filename_period(
        [book1, book2, book3, book4, book5, book6, book7, book8, book9]
    )

    assert len(result) == 9
    sorted_filenames = [book.locations[0].filename for book in result]

    assert sorted_filenames == [
        "wiki_2024-02a.zim",
        "wiki_2024-02.zim",
        "wiki_2024-01ba.zim",
        "wiki_2024-01aa.zim",
        "wiki_2024-01b.zim",
        "wiki_2024-01a.zim",
        "wiki_2024-01.zim",
        "wiki_2023-12aa.zim",
        "wiki_2023-12z.zim",
    ]


def test_invalid_filename_raises_error(
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
):
    """Book with invalid filename format should raise ValueError."""
    book = create_book()
    create_book_location(book=book, filename="invalid_filename.zim")

    with pytest.raises(ValueError, match="Unable to retrieve period from filename"):
        sort_books_by_filename_period([book])


def test_apply_retention_rules_keeps_last_version_of_two_most_recent_months(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
):
    """Retention rules should keep the last version of two most recent months."""
    title = create_title(name="test_wiki_en_all")
    now = getnow()

    # Create books from 4 different months, with multiple versions per month
    # Month 1 (oldest): 2024-01
    book1 = create_book(
        name="test_wiki",
        date="2024-01",
        flavour="nopic",
        created_at=now - timedelta(days=25),
    )
    book1.location_kind = "prod"
    book1.title = title
    create_book_location(book=book1, filename="test_wiki_2024-01.zim")

    # Month 2: 2024-02 with two versions
    book2a = create_book(
        name="test_wiki",
        date="2024-02",
        flavour="nopic",
        created_at=now - timedelta(days=40),
    )
    book2a.location_kind = "prod"
    book2a.title = title
    create_book_location(book=book2a, filename="test_wiki_2024-02.zim")

    book2b = create_book(
        name="test_wiki",
        date="2024-02",
        flavour="nopic",
        created_at=now - timedelta(days=39),
    )
    book2b.location_kind = "prod"
    book2b.title = title
    create_book_location(book=book2b, filename="test_wiki_2024-02a.zim")

    # Month 3: 2024-03 with three versions
    book3a = create_book(
        name="test_wiki",
        date="2024-03",
        flavour="nopic",
        created_at=now - timedelta(days=35),
    )
    book3a.location_kind = "prod"
    book3a.title = title
    create_book_location(book=book3a, filename="test_wiki_2024-03.zim")

    book3b = create_book(
        name="test_wiki",
        date="2024-03",
        flavour="nopic",
        created_at=now - timedelta(days=34),
    )
    book3b.location_kind = "prod"
    book3b.title = title
    create_book_location(book=book3b, filename="test_wiki_2024-03a.zim")

    book3c = create_book(
        name="test_wiki",
        date="2024-03",
        flavour="nopic",
        created_at=now - timedelta(days=33),
    )
    book3c.location_kind = "prod"
    book3c.title = title
    create_book_location(book=book3c, filename="test_wiki_2024-03b.zim")

    # Month 4 (newest): 2024-04 with two versions
    book4a = create_book(
        name="test_wiki",
        date="2024-04",
        flavour="nopic",
        created_at=now - timedelta(days=35),
    )
    book4a.location_kind = "prod"
    book4a.title = title
    create_book_location(book=book4a, filename="test_wiki_2024-04.zim")

    book4b = create_book(
        name="test_wiki",
        date="2024-04",
        flavour="nopic",
        created_at=now - timedelta(days=34),
    )
    book4b.location_kind = "prod"
    book4b.title = title
    create_book_location(book=book4b, filename="test_wiki_2024-04a.zim")

    dbsession.flush()

    with patch("cms_backend.mill.processors.title.getnow", return_value=now):
        apply_retention_rules(dbsession, title)

    dbsession.flush()

    # Keep book1 since it's created_at is still less than 30 days
    assert book1.location_kind == "prod"
    # Should keep only the latest from the two most recent months:
    # - 2024-04a
    # - 2024-03b
    assert book4b.location_kind == "prod"
    assert book3c.location_kind == "prod"

    # All others should be marked for deletion
    assert book2a.location_kind == "to_delete"
    assert book2b.location_kind == "to_delete"
    assert book3a.location_kind == "to_delete"
    assert book3b.location_kind == "to_delete"
    assert book4a.location_kind == "to_delete"


def test_apply_retention_rules_handles_different_flavours_separately(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
):
    """Retention rules should treat different flavours independently."""
    title = create_title(name="test_wiki_en_all")
    now = getnow()

    # Create books with "nopic" flavour: two in january and one in february
    book_nopic_jan = create_book(
        name="test_wiki",
        date="2024-01",
        flavour="nopic",
        created_at=now - timedelta(days=40),
    )
    book_nopic_jan.location_kind = "prod"
    book_nopic_jan.title = title
    create_book_location(book=book_nopic_jan, filename="test_wiki_nopic_2024-01.zim")

    book_nopic_jan_b = create_book(
        name="test_wiki",
        date="2024-01",
        flavour="nopic",
        created_at=now - timedelta(days=35),
    )
    book_nopic_jan_b.location_kind = "prod"
    book_nopic_jan_b.title = title
    create_book_location(book=book_nopic_jan_b, filename="test_wiki_nopic_2024-01a.zim")

    book_nopic_feb = create_book(
        name="test_wiki",
        date="2024-02",
        flavour="nopic",
        created_at=now - timedelta(days=40),
    )
    book_nopic_feb.location_kind = "prod"
    book_nopic_feb.title = title
    create_book_location(book=book_nopic_feb, filename="test_wiki_nopic_2024-02.zim")

    # Create books with "maxi" flavour
    book_maxi_jan = create_book(
        name="test_wiki",
        date="2024-01",
        flavour="maxi",
        created_at=now - timedelta(days=38),
    )
    book_maxi_jan.location_kind = "prod"
    book_maxi_jan.title = title
    create_book_location(book=book_maxi_jan, filename="test_wiki_maxi_2024-01.zim")

    book_maxi_feb = create_book(
        name="test_wiki",
        date="2024-02",
        flavour="maxi",
        created_at=now - timedelta(days=38),
    )
    book_maxi_feb.location_kind = "prod"
    book_maxi_feb.title = title
    create_book_location(book=book_maxi_feb, filename="test_wiki_maxi_2024-02.zim")

    dbsession.flush()

    with patch("cms_backend.mill.processors.title.getnow", return_value=now):
        apply_retention_rules(dbsession, title)

    dbsession.flush()

    # Only the first nopic_jan book should be deleted because in it's flavour,
    # there are two considered more recent than it.
    assert book_nopic_jan.location_kind == "to_delete"
    assert book_nopic_jan_b.location_kind == "prod"
    assert book_nopic_feb.location_kind == "prod"
    assert book_maxi_feb.location_kind == "prod"
    assert book_maxi_jan.location_kind == "prod"
