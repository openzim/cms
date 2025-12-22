from faker import Faker
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.book import create_book as db_create_book
from cms_backend.db.models import ZimfarmNotification


def test_create_book(
    dbsession: OrmSession, zimfarm_notification: ZimfarmNotification, faker: Faker
):
    """Create a book from a zimfarm notification"""
    book_id = zimfarm_notification.id  # Use zimfarm notification ID as book ID
    book = db_create_book(
        dbsession,
        book_id=book_id,
        article_count=faker.random_int(),
        media_count=faker.random_int(),
        size=faker.random_int(),
        zim_metadata={"key": "value"},
        zimcheck_result={"check_key": "check_value"},
        zimfarm_notification=zimfarm_notification,
    )
    dbsession.flush()
    assert book.zimfarm_notification == zimfarm_notification
    assert zimfarm_notification.book_id == book.id
    assert zimfarm_notification.book == book
    assert any(
        event
        for event in zimfarm_notification.events
        if "notification transformed into book" in event
    )
    assert any(
        event for event in book.events if "created from Zimfarm notification" in event
    )
