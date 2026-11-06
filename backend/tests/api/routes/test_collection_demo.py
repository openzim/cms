from collections.abc import Callable
from http import HTTPStatus
from pathlib import Path
from uuid import uuid4

import xxhash
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import (
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    Title,
    Warehouse,
)

ZIM_METADATA = {
    "Name": "test_title",
    "Title": "Test Title",
    "Description": "A test book",
    "Language": "eng",
    "Creator": "Test Creator",
    "Publisher": "Test Publisher",
    "Date": "2025-01-01",
}


def _add_title_to_collection(
    dbsession: OrmSession,
    collection: Collection,
    title: Title,
    path: str,
) -> None:
    ct = CollectionTitle(path=Path(path))
    ct.title = title
    ct.collection = collection
    dbsession.add(ct)
    dbsession.flush()


def _add_prod_book(
    dbsession: OrmSession,
    collection: Collection,
    title: Title,
    book: Book,
    *,
    path: str,
    warehouse: Warehouse,
    filename: str,
    create_book_location: Callable[..., BookLocation],
) -> None:
    _add_title_to_collection(dbsession, collection, title, path)
    book.title = title
    book.needs_processing = False
    book.has_error = False
    book.needs_file_operation = False
    book.location_kind = "prod"
    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=path,
        status="current",
        filename=filename,
    )
    dbsession.flush()


def test_head_collection_demo_html(
    client: TestClient,
    create_collection: Callable[..., Collection],
    access_token: str,
):
    collection = create_collection()
    response = client.head(
        f"/v1/collections/{collection.id}/demo.html",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    assert "text/html" in response.headers["content-type"]
    assert "ETag" in response.headers


def test_get_collection_demo_html_not_found(
    client: TestClient,
    access_token: str,
):
    response = client.get(
        f"/v1/collections/{uuid4()}/demo.html",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "Collection not found" in response.text


def test_get_collection_demo_html_empty(
    client: TestClient,
    create_collection: Callable[..., Collection],
    access_token: str,
):
    collection = create_collection(name="empty_collection")
    response = client.get(
        f"/v1/collections/{collection.id}/demo.html",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    assert "empty_collection" in response.text
    assert "No books are currently available" in response.text


def test_get_collection_demo_html_single_book(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
    access_token: str,
):
    warehouse = create_warehouse()
    collection = create_collection(
        name="demo_collection",
        warehouse=warehouse,
        download_base_url="https://download.kiwix.org/zim/",
        view_base_url="https://library.kiwix.org/content/",
    )
    title = create_title(name="test_title")

    book = create_book(zim_metadata={**ZIM_METADATA, "Flavour": "test"})
    _add_prod_book(
        dbsession,
        collection,
        title,
        book,
        path="wikipedia",
        warehouse=warehouse,
        filename="test_en_all.zim",
        create_book_location=create_book_location,
    )

    response = client.get(
        f"/v1/collections/{collection.id}/demo.html",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    assert "text/html" in response.headers["content-type"]
    expected_etag = xxhash.xxh64(response.content).hexdigest()
    assert response.headers["ETag"] == expected_etag

    assert "demo_collection" in response.text
    assert "Test Title" in response.text
    assert "A test book" in response.text
    assert "https://download.kiwix.org/zim/wikipedia/test_en_all.zim" in response.text
    assert "https://library.kiwix.org/content/test_en_all" in response.text
    assert ">Browse<" in response.text
    assert ">Download<" in response.text
