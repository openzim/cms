from collections.abc import Callable
from datetime import timedelta
from http import HTTPStatus
from typing import Any

import pytest
from dateutil.parser import isoparse
from fastapi.testclient import TestClient

from cms_backend.db.models import Book, ZimfarmNotification
from cms_backend.utils.datetime import getnow

# from sqlalchemy.orm import Session as OrmSession


@pytest.mark.parametrize(
    "payload,expected_status_code",
    [
        pytest.param(
            {
                "foo": "bar",
                "bar": "baz",
            },
            HTTPStatus.UNPROCESSABLE_CONTENT,
            id="missing-id",
        ),
        pytest.param(
            {
                "id": "foo",
                "foo": "bar",
                "bar": "baz",
            },
            HTTPStatus.UNPROCESSABLE_CONTENT,
            id="invalid-id",
        ),
        pytest.param(
            {
                "id": "2f154ad6-a9e6-4fe1-8f36-3764fbad3d9b",
                "foo": "bar",
                "bar": "baz",
            },
            HTTPStatus.ACCEPTED,
            id="valid-id",
        ),
    ],
)
def test_create_zimfarm_notification(
    client: TestClient,
    payload: dict[str, Any],
    expected_status_code: HTTPStatus,
):
    """Test create zimfarm_notification endpoint"""

    response = client.post(
        "/v1/zimfarm-notifications",
        json=payload,
    )
    assert response.status_code == expected_status_code
    if expected_status_code == HTTPStatus.ACCEPTED:
        response = client.get(f"/v1/zimfarm-notifications/{payload['id']}")
        response_doc = response.json()
        assert "id" in response_doc
        assert response_doc["id"] == payload["id"]
        assert "received_at" in response_doc
        received_at = isoparse(response_doc["received_at"])
        assert received_at.tzname() == "UTC"
        received_since = (getnow() - received_at.replace(tzinfo=None)).total_seconds()
        assert received_since > 0
        assert received_since < 3600
        assert "status" in response_doc
        assert response_doc["status"] == "pending"
        assert "content" in response_doc
        for key, value in payload.items():
            if key == "id":
                assert key not in response_doc["content"]
            else:
                assert key in response_doc["content"]
                assert response_doc["content"][key] == value


def test_create_zimfarm_notification_is_idempotent(
    client: TestClient,
    zimfarm_notification: ZimfarmNotification,
):
    """Test create zimfarm_notification endpoint"""

    response = client.get(f"/v1/zimfarm-notifications/{zimfarm_notification.id}")
    assert response.status_code == HTTPStatus.OK

    # try to recreate same Zimfarm notification with different data (to check this
    # data is ignored)
    payload = {
        "id": str(zimfarm_notification.id),
        "foo": "bar",
        "bar": "baz",
    }

    response = client.post(
        "/v1/zimfarm-notifications",
        json=payload,
    )

    assert response.status_code == HTTPStatus.ACCEPTED

    response = client.get(f"/v1/zimfarm-notifications/{zimfarm_notification.id}")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert "content" in response_doc
    for key in payload.keys():
        assert key not in response_doc["content"]
    for key in zimfarm_notification.content.keys():
        assert key in response_doc["content"]


def test_get_zimfarm_notifications_empty(client: TestClient):
    """Test get zimfarm_notifications endpoint with no notifications"""

    response = client.get("/v1/zimfarm-notifications")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert "meta" in response_doc
    assert response_doc["meta"]["count"] == 0
    assert response_doc["meta"]["skip"] == 0
    assert response_doc["meta"]["limit"] == 20
    assert response_doc["meta"]["page_size"] == 0
    assert "items" in response_doc
    assert response_doc["items"] == []


def test_get_zimfarm_notifications_with_data(
    client: TestClient,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
):
    """Test get zimfarm_notifications endpoint with notifications present"""

    # Create 5 notifications
    notifications: list[ZimfarmNotification] = []
    for i in range(5):
        notif = create_zimfarm_notification(
            content={"index": i, "data": f"notification_{i}"}
        )
        notifications.append(notif)

    response = client.get("/v1/zimfarm-notifications")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 5
    assert response_doc["meta"]["skip"] == 0
    assert response_doc["meta"]["limit"] == 20
    assert response_doc["meta"]["page_size"] == 5
    assert len(response_doc["items"]) == 5

    # Verify the structure of returned notifications
    for item in response_doc["items"]:
        assert "id" in item
        assert "book_id" in item
        assert "status" in item
        assert "received_at" in item
        # Light schema should NOT include content
        assert "content" not in item


def test_get_zimfarm_notifications_pagination(
    client: TestClient,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
):
    """Test get zimfarm_notifications endpoint with pagination"""

    # Create 10 notifications
    for i in range(10):
        create_zimfarm_notification(content={"index": i})

    # Test first page
    response = client.get("/v1/zimfarm-notifications?skip=0&limit=3")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 10
    assert response_doc["meta"]["skip"] == 0
    assert response_doc["meta"]["limit"] == 3
    assert response_doc["meta"]["page_size"] == 3
    assert len(response_doc["items"]) == 3

    # Test second page
    response = client.get("/v1/zimfarm-notifications?skip=3&limit=3")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 10
    assert response_doc["meta"]["skip"] == 3
    assert response_doc["meta"]["limit"] == 3
    assert response_doc["meta"]["page_size"] == 3
    assert len(response_doc["items"]) == 3

    # Test last page (partial)
    response = client.get("/v1/zimfarm-notifications?skip=9&limit=3")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 10
    assert response_doc["meta"]["skip"] == 9
    assert response_doc["meta"]["limit"] == 3
    assert response_doc["meta"]["page_size"] == 1
    assert len(response_doc["items"]) == 1


def test_get_zimfarm_notifications_filter_by_has_book(
    client: TestClient,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    create_book: Callable[..., Book],
):
    """Test get zimfarm_notifications endpoint filtering by has_book"""

    # Create 3 notifications with books
    for _ in range(3):
        notif = create_zimfarm_notification(content={"with_book": True})
        create_book(zimfarm_notification=notif)

    # Create 2 notifications without books
    for _ in range(2):
        create_zimfarm_notification(content={"with_book": False})

    # Filter for notifications with books
    response = client.get("/v1/zimfarm-notifications?has_book=true")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 3
    assert len(response_doc["items"]) == 3
    for item in response_doc["items"]:
        assert item["book_id"] is not None

    # Filter for notifications without books
    response = client.get("/v1/zimfarm-notifications?has_book=false")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 2
    assert len(response_doc["items"]) == 2
    for item in response_doc["items"]:
        assert item["book_id"] is None


def test_get_zimfarm_notifications_filter_by_status(
    client: TestClient,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    create_book: Callable[..., Book],
):
    """Test get zimfarm_notifications endpoint filtering by status"""

    # Create 2 processed notifications (with books)
    for _ in range(2):
        notif = create_zimfarm_notification(content={"status": "processed"})
        notif.status = "processed"
        create_book(zimfarm_notification=notif)

    # Create 2 errored notifications
    for _ in range(2):
        notif = create_zimfarm_notification(content={"status": "errored"})
        notif.status = "errored"

    # Create 2 bad_notification notifications
    for _ in range(2):
        notif = create_zimfarm_notification(content={"status": "bad_notification"})
        notif.status = "bad_notification"

    # Create 2 pending notifications (default)
    for _ in range(2):
        create_zimfarm_notification(content={"status": "pending"})

    # Filter for processed notifications
    response = client.get("/v1/zimfarm-notifications?status=processed")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 2
    assert len(response_doc["items"]) == 2
    for item in response_doc["items"]:
        assert item["status"] == "processed"

    # Filter for errored notifications
    response = client.get("/v1/zimfarm-notifications?status=errored")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 2
    assert len(response_doc["items"]) == 2
    for item in response_doc["items"]:
        assert item["status"] == "errored"

    # Filter for bad_notification notifications
    response = client.get("/v1/zimfarm-notifications?status=bad_notification")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 2
    assert len(response_doc["items"]) == 2
    for item in response_doc["items"]:
        assert item["status"] == "bad_notification"

    # Filter for pending notifications
    response = client.get("/v1/zimfarm-notifications?status=pending")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 2
    assert len(response_doc["items"]) == 2
    for item in response_doc["items"]:
        assert item["status"] == "pending"


def test_get_zimfarm_notifications_filter_by_date_range(
    client: TestClient,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
):
    """Test get zimfarm_notifications endpoint filtering by received_after/before"""

    now = getnow()
    yesterday = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)
    three_days_ago = now - timedelta(days=3)

    # Create notifications at different times
    create_zimfarm_notification(received_at=three_days_ago, content={"day": 3})
    create_zimfarm_notification(received_at=two_days_ago, content={"day": 2})
    create_zimfarm_notification(received_at=yesterday, content={"day": 1})
    create_zimfarm_notification(received_at=now, content={"day": 0})

    # Filter for notifications received after two days ago
    response = client.get(
        f"/v1/zimfarm-notifications?received_after={two_days_ago.isoformat()}"
    )
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 2  # yesterday and today

    # Filter for notifications received before yesterday
    response = client.get(
        f"/v1/zimfarm-notifications?received_before={yesterday.isoformat()}"
    )
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 2  # three days ago and two days ago

    # Filter for notifications in a specific range
    response = client.get(
        f"/v1/zimfarm-notifications?received_after={three_days_ago.isoformat()}&received_before={yesterday.isoformat()}"
    )
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 1  # only two days ago


def test_get_zimfarm_notifications_combined_filters(
    client: TestClient,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    create_book: Callable[..., Book],
):
    """Test get zimfarm_notifications endpoint with multiple filters combined"""

    # Create various notifications
    # 1. status=processed with book
    notif1 = create_zimfarm_notification(content={"case": 1})
    notif1.status = "processed"
    create_book(zimfarm_notification=notif1)

    # 2. status=bad_notification without book
    notif2 = create_zimfarm_notification(content={"case": 2})
    notif2.status = "bad_notification"

    # 3. status=pending with book (unusual but possible)
    notif3 = create_zimfarm_notification(content={"case": 3})
    notif3.status = "pending"
    create_book(zimfarm_notification=notif3)

    # 4. status=pending without book
    create_zimfarm_notification(content={"case": 4})

    # Filter for processed notifications with books
    response = client.get("/v1/zimfarm-notifications?status=processed&has_book=true")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 1

    # Filter for pending notifications without books
    response = client.get("/v1/zimfarm-notifications?status=pending&has_book=false")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 1


def test_get_zimfarm_notifications_filter_by_id(
    client: TestClient,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
):
    """Test get zimfarm_notifications endpoint passes id filter to database layer"""
    from uuid import UUID

    # Create notifications with specific UUIDs for partial matching
    notif1 = create_zimfarm_notification(
        _id=UUID("12345678-1234-5678-1234-567812345678"),
        content={"test": "notif1"},
    )
    create_zimfarm_notification(
        _id=UUID("87654321-4321-8765-4321-876543218765"),
        content={"test": "notif2"},
    )

    # Test that id parameter is passed through and filters correctly
    response = client.get("/v1/zimfarm-notifications?id=1234-5678")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 1
    assert response_doc["items"][0]["id"] == str(notif1.id)
