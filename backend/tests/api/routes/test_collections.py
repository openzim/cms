from collections.abc import Callable
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Collection, Title


def test_get_collections_empty(client: TestClient):
    """Test get collections endpoint with no collection"""

    response = client.get("/v1/collections")
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
    "skip,limit,expected_count",
    [
        pytest.param(0, 3, 3, id="first-page"),
        pytest.param(3, 3, 3, id="second-page"),
        pytest.param(6, 3, 2, id="third-page-partial"),
        pytest.param(8, 3, 0, id="page-num-too-high-no-results"),
        pytest.param(0, 1, 1, id="first-page-with-low-limit"),
        pytest.param(0, 20, 8, id="first-page-with-high-limit"),
    ],
)
def test_get_collections_pagination(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test that get_collections works correctly with skip and limit"""

    title1 = create_title(name="wikipedia_en_all")
    title2 = create_title(name="ted_en_all")
    title3 = create_title(name="gutenberg_en_all")

    # Create 8 collections with varying numbers of titles/paths
    for i in range(8):
        if i % 3 == 0:
            # Every third collection has multiple titles
            create_collection(
                title_ids_with_paths=[
                    (title1.id, f"/path/to/collection{i}/wikipedia"),
                    (title2.id, f"/path/to/collection{i}/ted"),
                ]
            )
        elif i % 3 == 1:
            # Some collections have a single title
            create_collection(
                title_ids_with_paths=[
                    (title3.id, f"/path/to/collection{i}/gutenberg"),
                ]
            )
        else:
            # Some collections have no titles
            create_collection()

    dbsession.flush()

    response = client.get(f"/v1/collections?skip={skip}&limit={limit}")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert "meta" in response_doc
    assert response_doc["meta"]["count"] == 8
    assert response_doc["meta"]["skip"] == skip
    assert response_doc["meta"]["limit"] <= limit
    assert response_doc["meta"]["page_size"] == expected_count
    assert "items" in response_doc
