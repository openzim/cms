from http import HTTPStatus
from typing import Any

import pytest
from dateutil.parser import isoparse
from fastapi.testclient import TestClient

from cms_backend.db.models import ZimfarmNotification
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
        assert "processed" in response_doc
        assert response_doc["processed"] is False
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
