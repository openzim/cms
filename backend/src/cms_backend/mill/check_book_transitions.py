from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.context import Context
from cms_backend.db.book import get_books_in_transition
from cms_backend.db.models import Book, BookTransitionStatus
from cms_backend.mill.context import Context as MillContext
from cms_backend.utils.datetime import getnow
from cms_backend.utils.filename import construct_download_url
from cms_backend.utils.requests import query_api

EXCLUDED_MIRROR_IDENT = "mirror.download.kiwix.org"
WORLDWIDE_SERVING = "Worldwide"


def _filename_without_suffix(filename: str) -> str:
    return filename[:-4] if filename.endswith(".zim") else filename


def _to_internal_url(url: str) -> str:
    """Rewrite a public-facing URL to the internal service address, if mapped."""
    parts = urlsplit(url)
    internal_host = MillContext.internal_host_mapping.get(parts.hostname or "")
    if internal_host is None:
        return url
    return urlunsplit(parts._replace(scheme="http", netloc=internal_host))


def _get_download_urls(book: Book) -> list[str]:
    """
    Get download URLs the book is expected to be served at, per destination.
    """
    if not book.filename or not book.title:
        return []
    if book.location_kind == "staging":
        return [
            construct_download_url(
                Context.staging_download_base_url, Path(""), book.filename
            )
        ]
    return [
        construct_download_url(tc.collection.download_base_url, tc.path, book.filename)
        for tc in book.title.collections
        if tc.collection.download_base_url
    ]


def _get_view_urls(book: Book) -> list[str]:
    """
    Get view URLs the book is expected to be served at, per destination.
    """
    if not book.filename or not book.title:
        return []
    name = _filename_without_suffix(book.filename)
    if book.location_kind == "staging":
        return [f"{Context.staging_view_base_url}{name}"]
    return [
        f"{tc.collection.view_base_url}{name}"
        for tc in book.title.collections
        if tc.collection.view_base_url
    ]


def _files_moved_to_destination(book: Book) -> bool:
    """Files have been moved by the shuttle to the destination warehouse."""
    if book.needs_file_operation:
        return False
    return not any(loc.status == "target" for loc in book.locations)


def _mirror_serves_worldwide(mirror: dict[str, Any]) -> bool:
    return (
        mirror.get("ident") != EXCLUDED_MIRROR_IDENT
        and mirror.get("online") is True
        and mirror.get("enabled") is True
        and mirror.get("serving") == WORLDWIDE_SERVING
    )


def _download_url_available_on_mirrors(download_url: str) -> bool:
    response = query_api(_to_internal_url(f"{download_url}.lb"), method="GET")
    if response.status_code != HTTPStatus.OK:
        return False
    return any(
        _mirror_serves_worldwide(mirror) for mirror in response.json.get("mirrors", [])
    )


def _available_on_enough_mirrors(book: Book) -> bool:
    """Book is available on enough mirrors (only when serving through the LB)."""
    lb_download_urls = [
        url
        for url in _get_download_urls(book)
        if urlsplit(url).netloc == Context.download_lb_host
    ]
    if not lb_download_urls:
        return True
    return all(_download_url_available_on_mirrors(url) for url in lb_download_urls)


def _content_url_is_live(content_url: str) -> bool:
    try:
        response = requests.get(
            _to_internal_url(content_url),
            timeout=Context.requests_timeout,
            allow_redirects=True,
        )
    except Exception:
        logger.exception(f"unexpected error while probing content url {content_url}")
        return False
    return response.status_code == HTTPStatus.OK


def _live_in_library(book: Book) -> bool:
    """Check that library catalog and live viewer serve the book."""
    content_urls = [
        view_url.replace("viewer#", "content/") for view_url in _get_view_urls(book)
    ]
    if not content_urls:
        return True
    return all(_content_url_is_live(url) for url in content_urls)


def _advance_transition(
    book: Book,
    next_status: BookTransitionStatus | None,
    event_message: str,
) -> None:
    """Move the transition cursor forward, recording the fulfilled condition.

    next_status is None when the transition is complete.
    """
    book.transition_status = next_status
    if next_status is None:
        book.transition_started_at = None
    book.events.append(f"{getnow()}: {event_message}")


def check_book_transition(book: Book) -> bool:
    """Check the next pending condition of a book's transition.

    Returns True when the transition advanced, False otherwise.
    """
    status = book.transition_status
    logger.debug(f"Book {book.id}: transition status '{status}'")

    if status == BookTransitionStatus.MOVING_FILES:
        if not _files_moved_to_destination(book):
            logger.debug(f"Book {book.id}: files have not been moved yet")
            return False
        _advance_transition(
            book,
            BookTransitionStatus.CHECKING_MIRRORS,
            f"files moved to {book.location_kind}",
        )
        logger.debug(f"Book {book.id}: files moved, now checking mirrors")
        return True

    if status == BookTransitionStatus.CHECKING_MIRRORS:
        if not _available_on_enough_mirrors(book):
            logger.debug(f"Book {book.id}: not available on enough mirrors yet")
            return False
        _advance_transition(
            book,
            BookTransitionStatus.CHECKING_LIBRARY,
            "available on enough mirrors",
        )
        logger.debug(
            f"Book {book.id}: available on enough mirrors, now checking library"
        )
        return True

    if status == BookTransitionStatus.CHECKING_LIBRARY:
        if not _live_in_library(book):
            logger.debug(f"Book {book.id}: not live in library yet")
            return False
        _advance_transition(
            book,
            None,
            f"move to {book.location_kind} complete",
        )
        logger.debug(f"Book {book.id}: live in library, transition complete")
        return True

    logger.warning(f"Book {book.id}: unexpected transition status '{status}'")
    return False


def check_book_transitions(session: OrmSession) -> None:
    """Check the next pending condition of every book in transition."""
    logger.info("Checking books in transition")
    books = get_books_in_transition(session)
    nb_advanced = 0
    for book in books:
        try:
            if check_book_transition(book):
                nb_advanced += 1
        except Exception:
            logger.exception(f"Error while checking transition for book {book.id}")
        session.commit()
    logger.info(
        f"Checked {len(books)} book(s) in transition, advanced {nb_advanced} of them"
    )
