from collections.abc import Callable
from http import HTTPStatus
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.token import generate_access_token
from cms_backend.db.models import Book, Collection, Title, User
from cms_backend.roles import RoleEnum
from cms_backend.utils.datetime import getnow


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
    assert set(data["items"][0].keys()) == {
        "id",
        "name",
        "maturity",
    }
    assert data["items"][0]["name"] == "wikipedia_fr_all"


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.EDITOR, HTTPStatus.OK, id="editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_create_title_required_permissions(
    client: TestClient,
    create_user: Callable[..., User],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test creating a title with different roles"""
    title_data = {
        "name": "wikipedia_en_test",
    }

    user = create_user(permission=permission)
    access_token = generate_access_token(user_id=str(user.id), issue_time=getnow())
    response = client.post(
        "/v1/titles",
        json=title_data,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


def test_create_title_required_fields_only(
    client: TestClient,
    dbsession: OrmSession,
    access_token: str,
):
    """Test creating a title with only required fields"""
    title_data = {
        "name": "wikipedia_en_test",
    }

    response = client.post(
        "/v1/titles",
        json=title_data,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert "id" in data
    assert "name" in data
    assert data["name"] == "wikipedia_en_test"

    # Verify the title was created in the database
    title = dbsession.get(Title, data["id"])
    assert title is not None
    assert title.name == "wikipedia_en_test"


def test_create_title_all_fields(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    access_token: str,
):
    """Test creating a title with all fields"""
    collection = create_collection(name="wikipedia")
    title_data = {
        "name": "wikipedia_en_test",
        "maturity": "dev",
        "collection_titles": [
            {
                "collection_name": "wikipedia",
                "path": "wikis",
            }
        ],
    }

    response = client.post(
        "/v1/titles",
        json=title_data,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert "id" in data
    assert "name" in data
    assert data["name"] == "wikipedia_en_test"
    assert "maturity" in data
    assert data["maturity"] == "dev"

    # Verify the title was created in the database and belongs to the collection
    title = dbsession.get(Title, data["id"])
    assert title is not None
    assert title.name == "wikipedia_en_test"
    assert str(title.collections[0].path) == "wikis"
    assert title.collections[0].collection_id == collection.id


def test_create_title_with_duplicate_collection_name(
    client: TestClient,
    access_token: str,
):
    """Test creating a title with the same collection repeated."""
    title_data = {
        "name": "wikipedia_en_test",
        "maturity": "dev",
        "collection_titles": [
            {
                "collection_name": "wikipedia",
                "path": "wikis",
            },
            {"collection_name": "wikipedia", "path": "other"},
        ],
    }

    response = client.post(
        "/v1/titles",
        json=title_data,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_create_title_duplicate_name(
    client: TestClient,
    access_token: str,
):
    """Test creating a title with duplicate name returns conflict error"""
    title_data = {
        "name": "wikipedia_en_duplicate",
    }

    # Create the first title
    response = client.post(
        "/v1/titles",
        json=title_data,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK

    # Try to create another title with the same name
    response = client.post(
        "/v1/titles",
        json=title_data,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert "already exists" in response.json()["message"].lower()


def test_get_title_by_id(
    client: TestClient,
    create_title: Callable[..., Title],
):
    """Test retrieving a title by ID returns full details"""
    title = create_title(
        name="wikipedia_en_test",
    )

    response = client.get(f"/v1/titles/{title.id}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    # Verify TitleFullSchema fields
    assert set(data.keys()) == {
        "id",
        "name",
        "maturity",
        "events",
        "books",
        "collections",
    }

    # Verify field values
    assert data["id"] == str(title.id)
    assert data["name"] == "wikipedia_en_test"
    assert isinstance(data["events"], list)
    assert isinstance(data["books"], list)
    assert len(data["books"]) == 0


def test_get_title_by_id_with_books(
    client: TestClient,
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    """Test retrieving a title with associated books"""
    title = create_title(
        name="wikipedia_en_test",
    )

    # Create books associated with this title
    book1 = create_book(
        zim_metadata={"Name": "wikipedia_en_test"},
    )
    book2 = create_book(
        zim_metadata={"Name": "wikipedia_en_test"},
    )

    # Associate books with title
    title.books.append(book1)
    title.books.append(book2)
    dbsession.flush()

    response = client.get(f"/v1/titles/{title.id}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    # Verify books are included
    assert len(data["books"]) == 2
    assert set(data["books"][0].keys()) == {
        "id",
        "title_id",
        "needs_processing",
        "has_error",
        "needs_file_operation",
        "location_kind",
        "created_at",
        "name",
        "date",
        "flavour",
    }
    assert data["books"][0]["title_id"] == str(title.id)
    assert data["books"][1]["title_id"] == str(title.id)

    # Verify book IDs match
    book_ids_in_response = {book["id"] for book in data["books"]}
    assert str(book1.id) in book_ids_in_response
    assert str(book2.id) in book_ids_in_response


def test_get_title_by_id_not_found(client: TestClient):
    """Test retrieving a non-existent title returns 404"""
    non_existent_id = uuid4()
    response = client.get(f"/v1/titles/{non_existent_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "does not exist" in response.json()["message"].lower()


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.EDITOR, HTTPStatus.OK, id="editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_update_title_required_permissions(
    client: TestClient,
    create_user: Callable[..., User],
    create_title: Callable[..., Title],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test updating a title with different roles"""
    title = create_title(name="wikipedia_en_test")
    update_data = {
        "maturity": "robust",
    }

    user = create_user(permission=permission)
    access_token = generate_access_token(user_id=str(user.id), issue_time=getnow())
    response = client.patch(
        f"/v1/titles/{title.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


def test_update_title_maturity(
    client: TestClient,
    create_title: Callable[..., Title],
    access_token: str,
):
    """Test updating a title's maturity"""
    title = create_title(name="wikipedia_en_test")
    assert title.maturity == "dev"

    update_data = {
        "maturity": "robust",
    }

    response = client.patch(
        f"/v1/titles/{title.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert data["id"] == str(title.id)
    assert data["name"] == "wikipedia_en_test"
    assert data["maturity"] == "robust"
