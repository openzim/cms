from collections.abc import Callable
from http import HTTPStatus
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.token import generate_access_token
from cms_backend.db.models import Account, Title, ZimfarmRecipe
from cms_backend.db.zimfarm_recipe import update_zimfarm_recipe
from cms_backend.roles import RoleEnum
from cms_backend.utils.datetime import getnow


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
def test_get_zimfarm_recipe_history(
    dbsession: OrmSession,
    client: TestClient,
    create_title: Callable[..., Title],
    create_zimfarm_recipe: Callable[..., ZimfarmRecipe],
    access_token: str,
    account: Account,
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test retrieving zimfarm recipe history"""
    title = create_title(name="wikipedia_en_test")
    recipe = create_zimfarm_recipe(title_id=title.id)
    for flavour in ["mini", "maxi", "nopic", "", "novid"]:
        update_zimfarm_recipe(
            dbsession,
            recipe=recipe,
            author=account,
            flavours=[flavour],
            title=title,
            old_recipes=set(),
            create_event=False,
        )
    response = client.get(
        f"/v1/recipes/{recipe.id}/history?skip={skip}&limit={limit}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["meta"]["skip"] == skip
    assert data["meta"]["limit"] == limit
    assert data["meta"]["page_size"] == expected_count
    assert len(data["items"]) == expected_count


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.EDITOR, HTTPStatus.OK, id="editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_get_zimfarm_recipe_history_required_permissions(
    client: TestClient,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
    create_zimfarm_recipe: Callable[..., ZimfarmRecipe],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test retrieving zimfarm recipe history with different roles"""
    title = create_title(name="wikipedia_en_test")
    recipe = create_zimfarm_recipe(title_id=title.id)

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.get(
        f"/v1/recipes/{recipe.name}/history?skip=0&limit=10",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code
