import datetime
from collections.abc import Callable
from http import HTTPStatus
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.token import generate_access_token
from cms_backend.context import Context
from cms_backend.db.models import (
    Account,
    Book,
    BookLocation,
    Collection,
    Event,
    Title,
    TitleFlavour,
    TitleUpload,
    Warehouse,
)
from cms_backend.db.title import update_title
from cms_backend.roles import RoleEnum
from cms_backend.schemas.models import TitleUpdateSchema
from cms_backend.utils.datetime import getnow
from cms_backend.utils.requests import Response


@pytest.fixture(autouse=True)
def setup_s3_mocks(monkeypatch: pytest.MonkeyPatch):
    """Set up required Context values for S3 upload tests."""
    monkeypatch.setattr(
        Context,
        "zim_upload_s3_bucket_uri",
        "s3+http://minio:9000/?keyId=minio_key&secretAccessKey=minio_secret&bucketName=uploads",
    )


def _mock_query_api_response(
    status_code: int = HTTPStatus.OK,
    json_data: dict[str, Any] | None = None,
    *,
    success: bool = True,
) -> MagicMock:
    """Create a mock for query_api that returns a Response-like object."""
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = status_code
    mock_response.success = success
    mock_response.json = json_data if json_data is not None else {}
    return mock_response


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


def test_get_titles_only_rotten_titles(
    client: TestClient, create_title: Callable[..., Title], access_token: str
):
    title1 = create_title(name="test_en_all1", flavours=["maxi", "mini"])
    title1.flavours[0].last_book_added_at = datetime.datetime.fromtimestamp(0)

    create_title(name="test_en_all2", flavours=["maxi", "mini"])

    response = client.get(
        "/v1/titles/?skip=0&liit=10&is_rotten=true",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    data = response.json()
    assert data["meta"]["count"] == 1
    assert data["items"][0]["id"] == str(title1.id)


def test_get_titles_skip_rotten_titles(
    client: TestClient, create_title: Callable[..., Title], access_token: str
):
    title1 = create_title(name="test_en_all1", flavours=["maxi", "mini"])
    title1.flavours[0].last_book_added_at = datetime.datetime.fromtimestamp(0)

    title2 = create_title(name="test_en_all2", flavours=["maxi", "mini"])

    response = client.get(
        "/v1/titles/?skip=0&liit=10&is_rotten=false",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    data = response.json()
    assert data["meta"]["count"] == 1
    assert data["items"][0]["id"] == str(title2.id)


def test_get_titles(
    client: TestClient,
    create_title: Callable[..., Title],
    access_token: str,
):
    """Test that get_titles returns titles"""
    create_title(name="wikipedia_en_all")
    create_title(name="wikipedia_fr_all")

    response = client.get(
        "/v1/titles?skip=1&limit=12",
        headers={"Authorization": f"Bearer {access_token}"},
    )
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
        "archived",
        "title",
        "creator",
        "publisher",
        "description",
        "language",
        "illustration_48x48_at_1",
        "long_description",
        "relation",
        "source",
        "license",
    }
    assert data["items"][0]["name"] == "wikipedia_fr_all"


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.OK, id="global-editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_create_title_required_permissions(
    client: TestClient,
    create_account: Callable[..., Account],
    illustration_48x48_at_1: str,
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test creating a title with different roles"""
    title_data = {
        "name": "wikipedia_en_test",
        "title": "Wikipedia in English",
        "creator": "Wikipedia Contributors",
        "publisher": "Kiwix",
        "language": "eng",
        "description": "A free encyclopedia",
        "illustration_48x48_at_1": illustration_48x48_at_1,
    }

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
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
    illustration_48x48_at_1: str,
):
    """Test creating a title with only required fields"""
    title_data = {
        "name": "wikipedia_en_test",
        "title": "Wikipedia in English",
        "creator": "Wikipedia Contributors",
        "publisher": "Kiwix",
        "language": "eng",
        "description": "A free encyclopedia",
        "illustration_48x48_at_1": illustration_48x48_at_1,
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
    assert data["title"] == "Wikipedia in English"
    assert data["creator"] == "Wikipedia Contributors"
    assert data["publisher"] == "Kiwix"
    assert data["language"] == "eng"
    assert data["description"] == "A free encyclopedia"
    assert data["illustration_48x48_at_1"] == illustration_48x48_at_1

    # Verify the title was created in the database
    title = dbsession.get(Title, data["id"])
    assert title is not None
    assert title.name == "wikipedia_en_test"

    events = dbsession.scalars(
        select(Event).where(Event.topic == "title_modified")
    ).all()
    assert len(events) == 1
    assert events[0].payload["action"] == "created"
    assert events[0].payload["name"] == "wikipedia_en_test"
    assert events[0].payload["id"] == str(title.id)


def test_create_title_all_fields(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    access_token: str,
    illustration_48x48_at_1: str,
):
    """Test creating a title with all fields"""
    collection = create_collection(name="wikipedia")
    title_data = {
        "name": "wikipedia_en_test",
        "maturity": "unstable",
        "title": "Wikipedia in English",
        "creator": "Wikipedia Contributors",
        "publisher": "Kiwix",
        "language": "eng",
        "description": "A free encyclopedia",
        "long_description": "Wikipedia is a free online encyclopedia.",
        "illustration_48x48_at_1": illustration_48x48_at_1,
        "license": "CC-BY-SA",
        "relation": "wikipedia",
        "source": "https://en.wikipedia.org",
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
    assert data["maturity"] == "unstable"
    assert data["title"] == "Wikipedia in English"
    assert data["creator"] == "Wikipedia Contributors"
    assert data["publisher"] == "Kiwix"
    assert data["language"] == "eng"
    assert data["description"] == "A free encyclopedia"
    assert data["long_description"] == "Wikipedia is a free online encyclopedia."
    assert data["illustration_48x48_at_1"] == illustration_48x48_at_1
    assert data["license"] == "CC-BY-SA"
    assert data["relation"] == "wikipedia"
    assert data["source"] == "https://en.wikipedia.org"

    # Verify the title was created in the database and belongs to the collection
    title = dbsession.get(Title, data["id"])
    assert title is not None
    assert title.name == "wikipedia_en_test"
    assert title.title == "Wikipedia in English"
    assert title.creator == "Wikipedia Contributors"
    assert title.publisher == "Kiwix"
    assert title.language == "eng"
    assert title.description == "A free encyclopedia"
    assert title.long_description == "Wikipedia is a free online encyclopedia."
    assert title.illustration_48x48_at_1 == illustration_48x48_at_1
    assert title.license == "CC-BY-SA"
    assert title.relation == "wikipedia"
    assert title.source == "https://en.wikipedia.org"
    assert str(title.collections[0].path) == "wikis"
    assert title.collections[0].collection_id == collection.id

    events = dbsession.scalars(
        select(Event).where(Event.topic == "title_modified")
    ).all()
    assert len(events) == 1
    assert events[0].payload["action"] == "created"
    assert events[0].payload["name"] == "wikipedia_en_test"
    assert events[0].payload["id"] == str(title.id)


def test_create_title_with_duplicate_collection_name(
    client: TestClient,
    access_token: str,
    illustration_48x48_at_1: str,
):
    """Test creating a title with the same collection repeated."""
    title_data = {
        "name": "wikipedia_en_test",
        "maturity": "unstable",
        "title": "Wikipedia in English",
        "creator": "Wikipedia Contributors",
        "publisher": "Kiwix",
        "language": "eng",
        "description": "A free encyclopedia",
        "illustration_48x48_at_1": illustration_48x48_at_1,
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
    illustration_48x48_at_1: str,
):
    """Test creating a title with duplicate name returns conflict error"""
    title_data = {
        "name": "wikipedia_en_duplicate",
        "title": "Wikipedia in English",
        "creator": "Wikipedia Contributors",
        "publisher": "Kiwix",
        "language": "eng",
        "description": "A free encyclopedia",
        "illustration_48x48_at_1": illustration_48x48_at_1,
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
    access_token: str,
):
    """Test retrieving a title by ID returns full details"""
    title = create_title(
        name="wikipedia_en_test",
    )

    response = client.get(
        f"/v1/titles/{title.id}", headers={"Authorization": f"Bearer {access_token}"}
    )
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
        "archived",
        "title",
        "creator",
        "publisher",
        "description",
        "language",
        "illustration_48x48_at_1",
        "long_description",
        "relation",
        "source",
        "license",
        "flavours",
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
    access_token: str,
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

    response = client.get(
        f"/v1/titles/{title.id}", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    # Verify books are included
    assert len(data["books"]) == 2
    assert set(data["books"][0].keys()) == {
        "id",
        "title_id",
        "title_name",
        "needs_processing",
        "has_error",
        "needs_file_operation",
        "location_kind",
        "created_at",
        "name",
        "date",
        "flavour",
        "deletion_date",
        "issues",
        "offliner",
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
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.OK, id="global-editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_update_title_required_permissions(
    client: TestClient,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test updating a title with different roles"""
    title = create_title(name="wikipedia_en_test")
    update_data = {
        "maturity": "stable",
    }

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.patch(
        f"/v1/titles/{title.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


def test_update_title(
    client: TestClient,
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    access_token: str,
):
    """Test updating a title's data"""
    title = create_title(name="wikipedia_en_test")
    assert title.maturity == "unstable"

    update_data = {
        "maturity": "stable",
        "name": "wikipedia_en_all",
    }

    response = client.patch(
        f"/v1/titles/{title.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert data["id"] == str(title.id)
    assert data["name"] == "wikipedia_en_all"
    assert data["maturity"] == "stable"

    events = dbsession.scalars(
        select(Event).where(Event.topic == "title_modified")
    ).all()
    assert len(events) == 1
    assert events[0].payload["action"] == "updated"
    assert events[0].payload["name"] == "wikipedia_en_all"
    assert events[0].payload["id"] == str(title.id)


def test_update_title_with_existing_title_name(
    client: TestClient,
    create_title: Callable[..., Title],
    access_token: str,
):
    """Test updating a title's data"""
    create_title(name="wikipedia_fr_test")
    title = create_title(name="wikipedia_en_test")
    update_data = {
        "maturity": "stable",
        "name": "wikipedia_fr_test",
    }

    response = client.patch(
        f"/v1/titles/{title.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.CONFLICT


def test_update_title_metadata(
    client: TestClient,
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    access_token: str,
    illustration_48x48_at_1: str,
):
    """Test updating a title's metadata fields"""
    title = create_title(name="wikipedia_en_test")

    update_data = {
        "title": "Wikipedia in English",
        "creator": "Wikipedia Contributors",
        "publisher": "Kiwix",
        "language": "eng",
        "description": "A free encyclopedia",
        "long_description": "Wikipedia is a free online encyclopedia.",
        "illustration_48x48_at_1": illustration_48x48_at_1,
        "license": "CC-BY-SA",
        "relation": "wikipedia",
        "source": "https://en.wikipedia.org",
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
    assert data["title"] == "Wikipedia in English"
    assert data["creator"] == "Wikipedia Contributors"
    assert data["publisher"] == "Kiwix"
    assert data["language"] == "eng"
    assert data["description"] == "A free encyclopedia"
    assert data["long_description"] == "Wikipedia is a free online encyclopedia."
    assert data["illustration_48x48_at_1"] == illustration_48x48_at_1
    assert data["license"] == "CC-BY-SA"
    assert data["relation"] == "wikipedia"
    assert data["source"] == "https://en.wikipedia.org"

    # Verify the metadata was updated in the database
    dbsession.refresh(title)
    assert title.title == "Wikipedia in English"
    assert title.creator == "Wikipedia Contributors"
    assert title.publisher == "Kiwix"
    assert title.language == "eng"
    assert title.description == "A free encyclopedia"
    assert title.long_description == "Wikipedia is a free online encyclopedia."
    assert title.illustration_48x48_at_1 == illustration_48x48_at_1
    assert title.license == "CC-BY-SA"
    assert title.relation == "wikipedia"
    assert title.source == "https://en.wikipedia.org"


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.OK, id="global-editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_archive_title_required_permissions(
    client: TestClient,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test archiving a title with different roles"""
    title = create_title(name="wikipedia_en_test")
    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.patch(
        f"/v1/titles/{title.id}/archive",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.NO_CONTENT, id="global-editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_archive_multiple_titles_required_permissions(
    client: TestClient,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test archiving multiple titles with different roles"""
    title1 = create_title(name="wikipedia_en_test")
    title2 = create_title(name="wikipedia_fr_test")

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.post(
        "/v1/titles/archive",
        json={"title_names": [title1.name, title2.name]},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.OK, id="global-editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_restore_archived_title_required_permissions(
    client: TestClient,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test restoring an archived title with different roles"""
    title = create_title(name="wikipedia_en_test", archived=True)
    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.patch(
        f"/v1/titles/{title.id}/restore",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.NO_CONTENT, id="global-editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_restore_multiple_titles_required_permissions(
    client: TestClient,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test archiving multiple titles with different roles"""
    title1 = create_title(name="wikipedia_en_test", archived=True)
    title2 = create_title(name="wikipedia_fr_test", archived=True)

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.post(
        "/v1/titles/restore",
        json={"title_names": [title1.name, title2.name]},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


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
def test_get_title_history(
    dbsession: OrmSession,
    client: TestClient,
    create_title: Callable[..., Title],
    access_token: str,
    account: Account,
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test retrieving title history"""
    title = create_title(name="wikipedia_en_test")
    for i in range(5):
        update_title(
            dbsession,
            title_identifier=str(title.id),
            author_id=account.id,
            payload=TitleUpdateSchema(
                title=f"Wikipedia Version {i}",
                comment=f"Update {i}",
            ),
        )

    response = client.get(
        f"/v1/titles/{title.id}/history?skip={skip}&limit={limit}",
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
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.OK, id="global-editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_get_title_history_required_permissions(
    client: TestClient,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test retrieving title history with different roles"""
    title = create_title(name="wikipedia_en_test")

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.get(
        f"/v1/titles/{title.id}/history?skip=0&limit=10",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


def test_get_title_history_entry(
    client: TestClient,
    create_title: Callable[..., Title],
    access_token: str,
):
    """Test retrieving a specific history entry using title name"""
    title = create_title(name="wikipedia_en_test")
    history_id = title.history_entries[0].id
    response = client.get(
        f"/v1/titles/{title.name}/history/{history_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.OK, id="global-editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_revert_title_required_permissions(
    dbsession: OrmSession,
    client: TestClient,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test reverting a title with different roles"""
    title = create_title(name="wikipedia_en_test")
    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    title = update_title(
        dbsession,
        title_identifier=str(title.id),
        author_id=account.id,
        payload=TitleUpdateSchema(
            title="Wikipedia Version 1",
            comment="Update 1",
        ),
    )
    assert len(title.history_entries) == 2
    history_id = title.history_entries[0].id
    response = client.patch(
        f"/v1/titles/{title.id}/revert/{history_id}",
        json={"comment": "Reverting"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.OK, id="global-editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_merge_titles_required_permissions(
    dbsession: OrmSession,
    client: TestClient,
    create_account: Callable[..., Account],
    create_warehouse: Callable[..., Warehouse],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_collection: Callable[..., Collection],
    monkeypatch: pytest.MonkeyPatch,
    create_title: Callable[..., Title],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test reverting a title with different roles"""
    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    warehouse = create_warehouse()
    monkeypatch.setattr(Context, "staging_warehouse_id", warehouse.id)
    monkeypatch.setattr(Context, "staging_base_path", Path("staging"))

    content = {
        "Name": "test_en_all",
        "Title": "Test Article",
        "Creator": "Test Creator",
        "Publisher": "Test Publisher",
        "Date": "2025-01-01",
        "Description": "Test description",
        "Language": "eng",
        "Illustration_48x48@1": (
            "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAOklEQVR4nO3OwQkAIAwA"
            "wfRf2u1gB4kfQeYKCHcNAAAAAAAAAAAAgL96bPf7EgAAAAAAAIC/egF5uwED0gQ8ugAAAA"
            "BJRU5ErkJggg=="
        ),
    }

    title1 = create_title(
        name="test_en_all",
        flavours=["maxi", "mini"],
        title=content["Title"],
        creator=content["Creator"],
        publisher=content["Publisher"],
        description=content["Description"],
        language=content["Language"],
        illustration_48x48_at_1=content["Illustration_48x48@1"],
    )
    book1 = create_book(zim_metadata=content, location_kind="staging")
    book1.title = title1
    create_book_location(
        book=book1,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2025-01.zim",
        status="current",
    )

    content2 = content.copy()
    content2["Name"] = "test_eng_all"
    content2["Date"] = "2025-02-02"
    title2 = create_title(
        name="test_eng_all",
        flavours=["maxi", "mini"],
        title=content["Title"],
        creator=content["Creator"],
        publisher=content["Publisher"],
        description=content["Description"],
        language=content["Language"],
        illustration_48x48_at_1=content["Illustration_48x48@1"],
    )
    book2 = create_book(zim_metadata=content2, location_kind="staging")
    book2.title = title2
    create_book_location(
        book=book2,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_eng_all_2025-02.zim",
        status="current",
    )

    create_collection(
        warehouse=warehouse,
        title_ids_with_paths=[(title1.id, "zim"), (title2.id, "zim")],
    )
    dbsession.flush()
    response = client.post(
        "/v1/titles/merge",
        json={"target": title1.name, "sources": [title2.name]},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "skip,limit,expected_count",
    [
        pytest.param(0, 3, 3, id="first-page"),
        pytest.param(3, 3, 1, id="second-page"),
        pytest.param(8, 3, 0, id="page-num-too-high-no-results"),
        pytest.param(0, 1, 1, id="first-page-with-low-limit"),
        pytest.param(0, 20, 4, id="first-page-with-high-limit"),
    ],
)
def test_get_title_flavours_pagination(
    dbsession: OrmSession,
    client: TestClient,
    create_title: Callable[..., Title],
    access_token: str,
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test retrieving title flavours"""
    title = create_title(name="wikipedia_en_test")
    flavours = ["maxi", "mini", "nopic", ""]
    for flavour in flavours:
        tf = TitleFlavour(flavour=flavour, recipe_id=None)
        tf.title = title
        dbsession.add(tf)
        dbsession.flush()

    response = client.get(
        f"/v1/titles/{title.id}/flavours?skip={skip}&limit={limit}",
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
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.OK, id="global-editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_delete_title_flavour_required_permissions(
    dbsession: OrmSession,
    client: TestClient,
    create_account: Callable[..., Account],
    create_title: Callable[..., Title],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test deleting title flavour with different roles"""
    title = create_title(name="wikipedia_en_test")
    tf = TitleFlavour(flavour="maxi", recipe_id=None)
    tf.title = title
    dbsession.add(tf)
    dbsession.flush()

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.delete(
        f"/v1/titles/{title.name}/flavours/maxi",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


def test_complete_upload_recipe_creation_bad_request(
    client: TestClient,
    title: Title,
    create_collection: Callable[..., Title],
    access_token: str,
):
    """Test that a bad request from zimfarm recipe creation raises BadRequestError."""
    create_collection(title_ids_with_paths=[(title.id, "other")])
    with (
        patch("cms_backend.api.routes.titles.get_kiwix_storage_client") as mock_get_s3,
        patch("cms_backend.api.routes.titles.complete_multipart_upload"),
        patch(
            "cms_backend.api.routes.titles.generate_view_presigned_url"
        ) as mock_presigned,
        patch("cms_backend.api.routes.titles.query_api") as mock_query_api,
        patch(
            "cms_backend.api.routes.titles.zimfarm_client_token_provider.get_authorization_header"
        ) as mock_auth_header,
    ):
        mock_s3_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_presigned.return_value = "https://example.com/presigned"
        mock_auth_header.return_value = {"Authorization": "Bearer fake-token"}

        mock_query_api.side_effect = [
            # Retrieiving recipe fails
            _mock_query_api_response(
                status_code=404, json_data={"error": "Not Found"}, success=False
            ),
            _mock_query_api_response(
                status_code=HTTPStatus.BAD_REQUEST,
                json_data={"error": "Invalid recipe config"},
                success=False,
            ),
        ]

        payload = {
            "upload_id": "test-upload-id",
            "key": "uploads/test-collection/test.zim",
            "parts": [{"part_number": 1, "etag": "etag1"}],
        }

        response = client.post(
            f"/v1/titles/{title.name}/upload/complete",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST


def test_complete_upload_recipe_creation_server_error(
    client: TestClient,
    title: Title,
    create_collection: Callable[..., Title],
    access_token: str,
):
    """Test that a server error from zimfarm recipe creation raises ServerError."""
    create_collection(title_ids_with_paths=[(title.id, "other")])
    with (
        patch("cms_backend.api.routes.titles.get_kiwix_storage_client") as mock_get_s3,
        patch("cms_backend.api.routes.titles.complete_multipart_upload"),
        patch(
            "cms_backend.api.routes.titles.generate_view_presigned_url"
        ) as mock_presigned,
        patch("cms_backend.api.routes.titles.query_api") as mock_query_api,
        patch(
            "cms_backend.api.routes.titles.zimfarm_client_token_provider.get_authorization_header"
        ) as mock_auth_header,
    ):
        mock_s3_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_presigned.return_value = "https://example.com/presigned"
        mock_auth_header.return_value = {"Authorization": "Bearer fake-token"}

        mock_query_api.side_effect = [
            # Retrieiving recipe fails
            _mock_query_api_response(
                status_code=404, json_data={"error": "Not Found"}, success=False
            ),
            # Recipe creation fails
            _mock_query_api_response(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                json_data={"error": "Internal error"},
                success=False,
            ),
        ]

        payload = {
            "upload_id": "test-upload-id",
            "key": "uploads/test-collection/test.zim",
            "parts": [{"part_number": 1, "etag": "etag1"}],
        }

        response = client.post(
            f"/v1/titles/{title.name}/upload/complete",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_complete_upload_missing_task_id(
    client: TestClient,
    title: Title,
    create_collection: Callable[..., Title],
    access_token: str,
):
    """Test that a missing task_id in the response raises ServerError."""
    create_collection(title_ids_with_paths=[(title.id, "other")])
    with (
        patch("cms_backend.api.routes.titles.get_kiwix_storage_client") as mock_get_s3,
        patch("cms_backend.api.routes.titles.complete_multipart_upload"),
        patch(
            "cms_backend.api.routes.titles.generate_view_presigned_url"
        ) as mock_presigned,
        patch("cms_backend.api.routes.titles.query_api") as mock_query_api,
        patch(
            "cms_backend.api.routes.titles.zimfarm_client_token_provider.get_authorization_header"
        ) as mock_auth_header,
    ):
        mock_s3_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_presigned.return_value = "https://example.com/presigned"
        mock_auth_header.return_value = {"Authorization": "Bearer access token"}

        mock_query_api.side_effect = [
            # Retrieiving recipe fails
            _mock_query_api_response(
                status_code=404, json_data={"error": "Not Found"}, success=False
            ),
            # Recipe creation succeeds
            _mock_query_api_response(
                status_code=201,
                json_data={"name": "zimwright_abc12345", "id": str(uuid4())},
            ),
            _mock_query_api_response(
                status_code=201,
                json_data={"name": "zimwright_abc12345", "id": str(uuid4())},
            ),
            # Task request succeeds but "requested" list is empty
            _mock_query_api_response(
                status_code=201,
                json_data={"requested": []},
            ),
        ]

        payload = {
            "upload_id": "test-upload-id",
            "key": "uploads/test-collection/test.zim",
            "parts": [{"part_number": 1, "etag": "etag1"}],
        }

        response = client.post(
            f"/v1/titles/{title.name}/upload/complete",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_complete_upload_persists_title_upload(
    dbsession: OrmSession,
    client: TestClient,
    title: Title,
    create_collection: Callable[..., Title],
    account: Account,
    access_token: str,
):
    """Test that a TitleUpload record is created in the database."""
    task_id = uuid4()
    create_collection(title_ids_with_paths=[(title.id, "other")])

    with (
        patch("cms_backend.api.routes.titles.get_kiwix_storage_client") as mock_get_s3,
        patch("cms_backend.api.routes.titles.complete_multipart_upload"),
        patch(
            "cms_backend.api.routes.titles.generate_view_presigned_url"
        ) as mock_presigned,
        patch("cms_backend.api.routes.titles.query_api") as mock_query_api,
        patch(
            "cms_backend.api.routes.titles.zimfarm_client_token_provider.get_authorization_header"
        ) as mock_auth_header,
    ):
        mock_s3_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_presigned.return_value = "https://example.com/presigned"
        mock_auth_header.return_value = {"Authorization": "Bearer access-token"}
        mock_query_api.side_effect = [
            # Retrieiving recipe fails
            _mock_query_api_response(
                status_code=404, json_data={"error": "Not Found"}, success=False
            ),
            # POST /recipes - create recipe
            _mock_query_api_response(
                status_code=HTTPStatus.CREATED,
                json_data={"name": "zimwright_abc12345", "id": str(uuid4())},
            ),
            _mock_query_api_response(
                status_code=HTTPStatus.CREATED,
                json_data={"name": "zimwright_abc12345", "id": str(uuid4())},
            ),
            # POST /requested-tasks - request task
            _mock_query_api_response(
                status_code=HTTPStatus.CREATED,
                json_data={"requested": [str(task_id)]},
            ),
            # DELETE /recipes/{name} - delete recipe
            _mock_query_api_response(status_code=HTTPStatus.OK),
        ]

        payload = {
            "upload_id": "test-upload-id",
            "key": "uploads/test-collection/test.zim",
            "parts": [{"part_number": 1, "etag": "etag1"}],
        }

        response = client.post(
            f"/v1/titles/{title.id}/upload/complete",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == HTTPStatus.OK

        title_upload = dbsession.get(TitleUpload, task_id)
        assert title_upload is not None
        assert title_upload.s3_key == "uploads/test-collection/test.zim"
        assert title_upload.requested_by_id == account.id
        assert title_upload.status == "requested"
