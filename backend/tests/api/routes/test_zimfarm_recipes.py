from collections.abc import Callable
from http import HTTPStatus
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from cms_backend.db.models import ZimfarmRecipe


@pytest.mark.parametrize(
    "skip, limit, expected_count",
    [
        pytest.param(0, 3, 3, id="first-page"),
        pytest.param(3, 3, 3, id="second-page"),
        pytest.param(6, 2, 0, id="page-num-too-high-no-results"),
        pytest.param(0, 1, 1, id="first-page-with-low-limit"),
        pytest.param(0, 10, 6, id="first-page-with-high-limit"),
    ],
)
def test_get_zimfarm_recipes(
    client: TestClient,
    create_zimfarm_recipe: Callable[..., ZimfarmRecipe],
    skip: int,
    limit: int,
    expected_count: int,
):
    for _ in range(6):
        create_zimfarm_recipe()

    response = client.get(f"/v1/recipes?skip={skip}&limit={limit}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["meta"]["skip"] == skip
    assert data["meta"]["limit"] == limit
    assert data["meta"]["page_size"] == expected_count
    assert len(data["items"]) == expected_count


def test_get_zimfarm_recipe_not_found(
    client: TestClient,
):
    response = client.get(f"/v1/recipes/{uuid4()}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_zimfarm_recipe(
    client: TestClient,
    create_zimfarm_recipe: Callable[..., ZimfarmRecipe],
):
    recipe = create_zimfarm_recipe()
    response = client.get(f"/v1/recipes/{recipe.name}")
    assert response.status_code == HTTPStatus.OK
