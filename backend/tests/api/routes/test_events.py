from collections.abc import Callable
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from cms_backend.db.models import Event


def test_get_events_empty(client: TestClient):
    """Test get events endpoint with no events"""

    response = client.get("/v1/events")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert "meta" in response_doc
    assert response_doc["meta"]["count"] == 0
    assert response_doc["meta"]["skip"] == 0
    assert response_doc["meta"]["limit"] == 20
    assert response_doc["meta"]["page_size"] == 0
    assert "items" in response_doc
    assert response_doc["items"] == []


@pytest.mark.parametrize(
    "topic,skip,limit,expected_results",
    [
        pytest.param(None, 0, 3, 3, id="first-page"),
        pytest.param(None, 3, 3, 3, id="second-page"),
        pytest.param(None, 0, 1, 1, id="first-page-with-low-limit"),
        pytest.param(None, 0, 10, 6, id="first-page-with-high-limit"),
        pytest.param(None, 10, 10, 0, id="page-num-too-high-no-results"),
        pytest.param("title_mod", 0, 10, 3, id="title-modified-topic"),
    ],
)
def test_get_events_pagination(
    client: TestClient,
    create_event: Callable[..., Event],
    topic: str | None,
    skip: int,
    limit: int,
    expected_results: int,
):
    """Test get events endpoint with pagination"""

    for _ in range(3):
        create_event(topic="title_created")

    for _ in range(3):
        create_event(topic="title_modified")

    # Test first page
    url = f"/v1/events?skip={skip}&limit={limit}"
    if topic:
        url += f"&topic={topic}"

    response = client.get(url)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["meta"]["skip"] == skip
    assert data["meta"]["limit"] == limit
    assert data["meta"]["page_size"] == expected_results
    assert len(data["items"]) == expected_results

    if topic and data["items"]:
        for item in data["items"]:
            assert topic in item["topic"]
