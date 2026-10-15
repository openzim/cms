from collections.abc import Callable
from typing import Any
from unittest.mock import Mock, patch

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.book import start_book_transition
from cms_backend.db.models import (
    Book,
    BookTransitionStatus,
    Collection,
    CollectionTitle,
    Title,
)
from cms_backend.mill import check_book_transitions as check_book_translations_module
from cms_backend.mill.check_book_transitions import check_book_transition
from cms_backend.mill.context import Context as MillContext
from cms_backend.utils.datetime import getnow
from cms_backend.utils.requests import Response

LB_DOWNLOAD_BASE_URL = "https://lb.download.kiwix.org/zim/"
PLAIN_DOWNLOAD_BASE_URL = "https://download.kiwix.org/zim/"
FILENAME = "test_en_all_2026-01.zim"


def _make_book_in_transition(
    *,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
    dbsession: OrmSession,
    download_base_url: str = LB_DOWNLOAD_BASE_URL,
    status: str = BookTransitionStatus.MOVING_FILES,
    needs_file_operation: bool = False,
) -> Book:
    title = create_title(name="test_en_all")
    collection = create_collection(name="test", download_base_url=download_base_url)
    create_collection_title(title=title, collection=collection, path="/zim/test")
    book = create_book(
        name="test_en_all", date="2026-01-15", flavour="", filename=FILENAME
    )
    book.title_id = title.id
    book.location_kind = "prod"
    book.needs_file_operation = needs_file_operation
    book.transition_status = status
    book.transition_started_at = getnow()
    dbsession.add(book)
    dbsession.flush()
    return book


def _mirrors_response(
    mirrors: list[dict[str, Any]], status_code: int = 200
) -> Response:
    return Response(
        status_code=status_code, success=status_code == 200, json={"mirrors": mirrors}
    )


def test_start_book_transition_is_idempotent(book: Book):
    assert book.transition_status is None

    start_book_transition(book)
    assert book.transition_status == BookTransitionStatus.MOVING_FILES
    started_at = book.transition_started_at
    assert started_at is not None

    # a second call must not reset an ongoing transition
    book.transition_status = BookTransitionStatus.CHECKING_LIBRARY
    start_book_transition(book)
    assert book.transition_status == BookTransitionStatus.CHECKING_LIBRARY
    assert book.transition_started_at == started_at


def test_files_moved_to_destination_waits_for_file_operation(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
):
    book = _make_book_in_transition(
        create_book=create_book,
        create_title=create_title,
        create_collection=create_collection,
        create_collection_title=create_collection_title,
        dbsession=dbsession,
        needs_file_operation=True,
    )

    assert check_book_transition(book) is False
    assert book.transition_status == BookTransitionStatus.MOVING_FILES


def test_files_moved_to_destination_advances_to_checking_mirrors(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
):
    book = _make_book_in_transition(
        create_book=create_book,
        create_title=create_title,
        create_collection=create_collection,
        create_collection_title=create_collection_title,
        dbsession=dbsession,
        needs_file_operation=False,
    )

    assert check_book_transition(book) is True
    assert book.transition_status == BookTransitionStatus.CHECKING_MIRRORS
    assert any("files moved" in event for event in book.events)


def test_available_on_enough_mirrors_skipped_without_load_balancer(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
):
    book = _make_book_in_transition(
        create_book=create_book,
        create_title=create_title,
        create_collection=create_collection,
        create_collection_title=create_collection_title,
        dbsession=dbsession,
        download_base_url=PLAIN_DOWNLOAD_BASE_URL,
        status=BookTransitionStatus.CHECKING_MIRRORS,
    )

    with patch.object(check_book_translations_module, "query_api") as mock_query:
        assert check_book_transition(book) is True
    mock_query.assert_not_called()
    assert book.transition_status == BookTransitionStatus.CHECKING_LIBRARY


def test_available_on_enough_mirrors_requires_worldwide_mirror(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
):
    book = _make_book_in_transition(
        create_book=create_book,
        create_title=create_title,
        create_collection=create_collection,
        create_collection_title=create_collection_title,
        dbsession=dbsession,
        status=BookTransitionStatus.CHECKING_MIRRORS,
    )

    mirrors = [
        {
            "ident": "ny.mirror.driftle.ss",
            "online": True,
            "enabled": True,
            "serving": "North America plus Americas",
        },
        {
            "ident": "mirror.download.kiwix.org",
            "online": True,
            "enabled": True,
            "serving": "Worldwide",
        },
    ]
    with (
        patch.object(
            MillContext,
            "internal_host_mapping",
            {"lb.download.kiwix.org": "lb-web-service.zim:80"},
        ),
        patch.object(
            check_book_translations_module,
            "query_api",
            return_value=_mirrors_response(mirrors),
        ),
    ):
        assert check_book_transition(book) is False
    assert book.transition_status == BookTransitionStatus.CHECKING_MIRRORS

    worldwide = [
        {
            "ident": "wi.mirror.driftle.ss",
            "online": True,
            "enabled": True,
            "serving": "Worldwide",
        }
    ]
    with (
        patch.object(
            MillContext,
            "internal_host_mapping",
            {"lb.download.kiwix.org": "lb-web-service.zim:80"},
        ),
        patch.object(
            check_book_translations_module,
            "query_api",
            return_value=_mirrors_response(worldwide),
        ) as mock_query,
    ):
        assert check_book_transition(book) is True
    assert mock_query.call_args.args[0].startswith("http://lb-web-service.zim:80/")
    assert book.transition_status == BookTransitionStatus.CHECKING_LIBRARY


def test_live_in_library_requires_live_content(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
):
    book = _make_book_in_transition(
        create_book=create_book,
        create_title=create_title,
        create_collection=create_collection,
        create_collection_title=create_collection_title,
        dbsession=dbsession,
        status=BookTransitionStatus.CHECKING_LIBRARY,
    )

    with (
        patch.object(
            MillContext,
            "internal_host_mapping",
            {"browse.library.kiwix.org": "prod-kiwix-browse-frontend-service.zim:80"},
        ),
        patch.object(
            check_book_translations_module.requests,
            "get",
            return_value=Mock(status_code=404),
        ),
    ):
        assert check_book_transition(book) is False
    assert book.transition_status == BookTransitionStatus.CHECKING_LIBRARY

    mock_requests = Mock(**{"get.return_value": Mock(status_code=200)})
    with (
        patch.object(
            MillContext,
            "internal_host_mapping",
            {"browse.library.kiwix.org": "prod-kiwix-browse-frontend-service.zim:80"},
        ),
        patch.object(check_book_translations_module, "requests", new=mock_requests),
    ):
        assert check_book_transition(book) is True
    assert mock_requests.get.call_args.args[0].startswith(
        "http://prod-kiwix-browse-frontend-service.zim:80/"
    )
    assert book.transition_status is None
    assert book.transition_started_at is None
    assert any("complete" in event for event in book.events)


def test_transition_check_uses_internal_host_with_custom_port(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
):
    """A mapped host is reached over HTTP on the configured (custom) port."""
    book = _make_book_in_transition(
        create_book=create_book,
        create_title=create_title,
        create_collection=create_collection,
        create_collection_title=create_collection_title,
        dbsession=dbsession,
        status=BookTransitionStatus.CHECKING_MIRRORS,
    )
    worldwide = [
        {
            "ident": "wi.mirror.driftle.ss",
            "online": True,
            "enabled": True,
            "serving": "Worldwide",
        }
    ]

    with (
        patch.object(
            MillContext,
            "internal_host_mapping",
            {"lb.download.kiwix.org": "lb-web-service.zim:8080"},
        ),
        patch.object(
            check_book_translations_module,
            "query_api",
            return_value=_mirrors_response(worldwide),
        ) as mock_query,
    ):
        assert check_book_transition(book) is True

    assert mock_query.call_args.args[0].startswith("http://lb-web-service.zim:8080/")
