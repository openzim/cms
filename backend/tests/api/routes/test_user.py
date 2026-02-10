from collections.abc import Callable
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from cms_backend.api.token import generate_access_token
from cms_backend.db.models import User
from cms_backend.utils.datetime import getnow


def test_create_user(client: TestClient, user: User):
    url = "/v1/users/"
    access_token = generate_access_token(
        issue_time=getnow(),
        user_id=str(user.id),
    )
    response = client.post(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "username": "test",
            "password": "test",
            "role": "viewer",
        },
    )
    assert response.status_code == HTTPStatus.OK


def test_create_user_duplicate(client: TestClient, user: User):
    url = "/v1/users/"
    access_token = generate_access_token(
        issue_time=getnow(),
        user_id=str(user.id),
    )
    response = client.post(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "username": user.username,
            "password": "test",
            "role": "viewer",
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.parametrize(
    "current,new,expected",
    [
        ("invalid", "test2", HTTPStatus.BAD_REQUEST),
        (None, "test2", HTTPStatus.BAD_REQUEST),
        ("testpassword", "test2", HTTPStatus.NO_CONTENT),
    ],
)
def test_update_user_password_invalid(
    client: TestClient,
    create_user: Callable[..., User],
    current: str,
    new: str,
    expected: HTTPStatus,
):
    """Test updating a user's password with an invalid current password"""
    user = create_user(password="testpassword")

    access_token = generate_access_token(
        issue_time=getnow(),
        user_id=str(user.id),
    )
    response = client.patch(
        f"/v1/users/{user.username}/password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"current": current, "new": new},
    )
    assert response.status_code == expected
