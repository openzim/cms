import re
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy.orm import Session as OrmSession
from tests.processors.test_book import GOOD_ZIM_METADATA

from cms_backend.db.models import Book, Title, ZimfarmNotification
from cms_backend.processors.zimfarm_notification import process_notification

GOOD_NOTIFICATION_CONTENT = {
    "article_count": 100,
    "media_count": 50,
    "size": 1024000,
    "metadata": GOOD_ZIM_METADATA,
    "zimcheck": {"status": "pass"},
    "url": "https://example.com/zim/test.zim",
}


def test_process_notification_success(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    title: Title,
):
    """Process notification successfully - all steps work"""

    notification = create_zimfarm_notification(content=GOOD_NOTIFICATION_CONTENT)
    assert len(notification.events) == 0
    assert len(title.events) == 0
    assert notification.processed is False
    assert notification.errored is False

    process_notification(dbsession, notification)

    dbsession.flush()
    assert notification.processed is True
    assert notification.errored is False
    assert notification.book is not None
    assert notification.book.title == title
    assert notification.book.title_id == title.id
    assert any(
        event
        for event in notification.events
        if re.match(".*: notification transformed into book", event)
    )
    assert any(
        event
        for event in notification.book.events
        if re.match(".*: created from Zimfarm notification", event)
    )
    assert any(
        event
        for event in notification.book.events
        if re.match(".*: book passed QA checks", event)
    )
    assert any(
        event
        for event in notification.book.events
        if re.match(".*: found matching title .*", event)
    )
    assert any(
        event
        for event in notification.book.events
        if re.match(".*: book added to title .*", event)
    )
    assert any(
        event for event in title.events if re.match(".*: book .* added to title", event)
    )


@pytest.mark.parametrize(
    "missing_key, notification_content",
    [
        pytest.param(
            missing_key,
            {
                key: value
                for key, value in GOOD_NOTIFICATION_CONTENT.items()
                if key != missing_key
            },
            id=f"missing-{missing_key}",
        )
        for missing_key in [
            "article_count",
            "media_count",
            "size",
            "metadata",
            "zimcheck",
            "url",
        ]
    ],
)
def test_process_notification_missing_mandatory_key(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    missing_key: str,
    notification_content: dict[str, Any],
):
    """Process notification with missing mandatory key in content"""

    notification = create_zimfarm_notification(content=notification_content)
    assert len(notification.events) == 0
    assert notification.processed is False
    assert notification.errored is False

    process_notification(dbsession, notification)

    dbsession.flush()
    assert notification.processed is True
    assert notification.errored is False
    assert notification.book is None
    assert any(
        event
        for event in notification.events
        if re.match(f".*: notification is missing mandatory keys: {missing_key}", event)
    )


def test_process_notification_missing_multiple_mandatory_keys(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
):
    """Process notification with multiple missing mandatory keys in content"""

    notification_content = {
        key: value
        for key, value in GOOD_NOTIFICATION_CONTENT.items()
        if key not in ["article_count", "size", "url"]
    }
    notification = create_zimfarm_notification(content=notification_content)
    assert len(notification.events) == 0
    assert notification.processed is False
    assert notification.errored is False

    process_notification(dbsession, notification)

    dbsession.flush()
    assert notification.processed is True
    assert notification.errored is False
    assert notification.book is None
    assert any(
        event
        for event in notification.events
        if re.match(
            ".*: notification is missing mandatory keys: article_count,size,url",
            event,
        )
    )


def test_process_notification_qa_check_fails(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    title: Title,  # noqa: ARG001
):
    """Process notification where book QA check fails due to missing metadata"""

    # Create notification with metadata missing the Creator field
    incomplete_metadata = {
        key: value for key, value in GOOD_ZIM_METADATA.items() if key != "Creator"
    }
    notification_content = {
        **GOOD_NOTIFICATION_CONTENT,
        "metadata": incomplete_metadata,
        "zim_metadata": incomplete_metadata,
    }
    notification = create_zimfarm_notification(content=notification_content)
    assert len(notification.events) == 0
    assert notification.processed is False
    assert notification.errored is False

    process_notification(dbsession, notification)

    dbsession.flush()
    assert notification.processed is True
    assert notification.errored is False
    assert notification.book is not None
    # Book was created but not added to title because QA failed
    assert notification.book.title is None
    assert notification.book.title_id is None
    assert any(
        event
        for event in notification.book.events
        if re.match(".*: book is missing mandatory metadata: Creator", event)
    )
    # Should not have these events since QA failed
    assert not any(
        event
        for event in notification.book.events
        if re.match(".*: book passed QA checks", event)
    )


def test_process_notification_no_matching_title(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    title: Title,  # noqa: ARG001
):
    """Process notification where no matching title exists in database"""

    # Use a different name that doesn't match the existing title
    different_metadata = {**GOOD_ZIM_METADATA, "Name": "different_title_name"}
    notification_content = {
        **GOOD_NOTIFICATION_CONTENT,
        "metadata": different_metadata,
        "zim_metadata": different_metadata,
    }
    notification = create_zimfarm_notification(content=notification_content)
    assert len(notification.events) == 0
    assert notification.processed is False
    assert notification.errored is False

    process_notification(dbsession, notification)

    dbsession.flush()
    assert notification.processed is True
    assert notification.errored is False
    assert notification.book is not None
    # Book was created and passed QA but not added to title
    assert notification.book.title is None
    assert notification.book.title_id is None
    assert any(
        event
        for event in notification.book.events
        if re.match(".*: book passed QA checks", event)
    )
    assert any(
        event
        for event in notification.book.events
        if re.match(".*: no matching title found for book", event)
    )
    # Should not have this event since title was not found
    assert not any(
        event
        for event in notification.book.events
        if re.match(".*: book added to title .*", event)
    )


def test_process_notification_missing_name(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    title: Title,  # noqa: ARG001
):
    """Process notification where book metadata has no Name field"""

    # Remove Name from metadata
    no_name_metadata = {
        key: value for key, value in GOOD_ZIM_METADATA.items() if key != "Name"
    }
    notification_content = {
        **GOOD_NOTIFICATION_CONTENT,
        "metadata": no_name_metadata,
    }
    notification = create_zimfarm_notification(content=notification_content)
    assert len(notification.events) == 0
    assert notification.processed is False
    assert notification.errored is False

    process_notification(dbsession, notification)

    dbsession.flush()
    assert notification.processed is True
    assert notification.errored is False
    assert notification.book is not None
    # Book was created but QA check fails because Name is missing
    assert notification.book.title is None
    assert notification.book.title_id is None
    # Name is a mandatory metadata field, so QA check should fail
    assert any(
        event
        for event in notification.book.events
        if re.match(".*: book is missing mandatory metadata: Name", event)
    )


def test_process_notification_exception_handling(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    title: Title,  # noqa: ARG001
):
    """Process notification with unexpected exception during processing"""

    notification = create_zimfarm_notification(content=GOOD_NOTIFICATION_CONTENT)
    assert len(notification.events) == 0
    assert notification.processed is False
    assert notification.errored is False

    # Simulate a very bad error by dropping the content attribute
    # (and adding it back so that SQLAlchemy does not choke during flush)
    save_content = notification.content
    del notification.content

    process_notification(dbsession, notification)

    notification.content = save_content
    dbsession.flush()

    assert notification.processed is True
    assert notification.errored is True
    assert any(
        event
        for event in notification.events
        if re.match(".*: error encountered while processing notification", event)
    )


def test_process_notification_empty_name(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    title: Title,  # noqa: ARG001
):
    """Process notification where book metadata has empty Name field"""

    # Set Name to empty string
    empty_name_metadata = {**GOOD_ZIM_METADATA, "Name": ""}
    notification_content = {
        **GOOD_NOTIFICATION_CONTENT,
        "metadata": empty_name_metadata,
        "zim_metadata": empty_name_metadata,
    }
    notification = create_zimfarm_notification(content=notification_content)
    assert len(notification.events) == 0
    assert notification.processed is False
    assert notification.errored is False

    process_notification(dbsession, notification)

    dbsession.flush()
    assert notification.processed is True
    assert notification.errored is False
    assert notification.book is not None
    # Book was created but not added to title because Name is empty
    assert notification.book.title is None
    assert notification.book.title_id is None
    assert any(
        event
        for event in notification.book.events
        if re.match(".*: no title can be found because name is missing", event)
    )


def test_process_notification_with_existing_books(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    create_book: Callable[..., Book],
    title: Title,
):
    """Process notification and add to title that already has books"""

    # Add an existing book to the title
    existing_book = create_book(zim_metadata={"Name": title.name})
    title.books.append(existing_book)
    dbsession.flush()

    assert len(title.books) == 1

    # Now process a new notification
    notification = create_zimfarm_notification(content=GOOD_NOTIFICATION_CONTENT)
    process_notification(dbsession, notification)

    dbsession.flush()
    assert notification.processed is True
    assert notification.errored is False
    assert notification.book is not None
    assert notification.book.title == title
    assert len(title.books) == 2
    assert existing_book in title.books
    assert notification.book in title.books
