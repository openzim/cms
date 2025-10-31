from collections.abc import Callable
from http import HTTPStatus

from fastapi.testclient import TestClient

from cms_backend.db.models import Title


def test_get_titles_empty(client: TestClient):
    """Test that get_titles returns empty list when no titles exist"""
    response = client.get("/v1/titles?skip=0&limit=10")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "meta" in data
    assert "items" in data
    assert data["meta"]["skip"] == 0
    assert data["meta"]["limit"] == 10
    assert data["meta"]["page_size"] == 0
    assert data["meta"]["count"] == 0
    assert data["items"] == []


def test_get_titles(
    client: TestClient,
    create_title: Callable[..., Title],
):
    """Test that get_titles returns titles"""
    create_title(name="wikipedia_en_all")
    create_title(name="wikipedia_fr_all")

    response = client.get("/v1/titles?skip=1&limit=12")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["meta"]["skip"] == 1
    assert data["meta"]["limit"] == 12
    assert data["meta"]["page_size"] == 1
    assert data["meta"]["count"] == 2
    assert len(data["items"]) == 1
    assert set(data["items"][0].keys()) == {"name"}
    assert data["items"][0]["name"] == "wikipedia_fr_all"
