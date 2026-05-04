from collections.abc import Callable
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from cms_backend.api.token import generate_access_token
from cms_backend.db.models import Account
from cms_backend.utils.datetime import getnow


def test_create_account(client: TestClient, account: Account):
    url = "/v1/accounts/"
    access_token = generate_access_token(
        issue_time=getnow(),
        account_id=str(account.id),
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


def test_create_account_duplicate(client: TestClient, account: Account):
    url = "/v1/accounts/"
    access_token = generate_access_token(
        issue_time=getnow(),
        account_id=str(account.id),
    )
    response = client.post(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "username": account.username,
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
def test_update_account_password_invalid(
    client: TestClient,
    create_account: Callable[..., Account],
    current: str,
    new: str,
    expected: HTTPStatus,
):
    """Test updating an account's password with an invalid current password"""
    account = create_account(password="testpassword")

    access_token = generate_access_token(
        issue_time=getnow(),
        account_id=str(account.id),
    )
    response = client.patch(
        f"/v1/accounts/{account.username}/password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"current": current, "new": new},
    )
    assert response.status_code == expected
