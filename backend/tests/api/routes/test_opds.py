from collections.abc import Callable
from http import HTTPStatus
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree as ET

import pytest
import xxhash
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.context import Context
from cms_backend.db.models import (
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    Title,
    Warehouse,
)
from cms_backend.utils.opds import (
    ACQUISITION_REL,
    ATOM_NAMESPACE,
    BITTORRENT_MIMETYPE,
    DC_NAMESPACE,
    ILLUSTRATION_MIMETYPE,
    KIWIX_NAMESPACE,
    METALINK_MIMETYPE,
    OPDS_MEDIA_TYPE,
    THUMBNAIL_MIMETYPE,
    THUMBNAIL_REL,
    ZIM_MIMETYPE,
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


def test_head_collection_opds_xml(
    client: TestClient,
    create_collection: Callable[..., Collection],
    access_token: str,
):
    collection = create_collection()
    response = client.head(
        f"/v1/collections/{collection.id}/opds.xml",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == OPDS_MEDIA_TYPE
    assert "ETag" in response.headers


def test_get_collection_opds_xml_not_found_by_id(
    client: TestClient,
    access_token: str,
):
    response = client.get(
        f"/v1/collections/{uuid4()}/opds.xml",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    root = ET.fromstring(response.text)
    assert root.tag == f"{{{ATOM_NAMESPACE}}}feed"
    assert list(root.findall(f"{{{ATOM_NAMESPACE}}}entry")) == []


def test_get_collection_opds_xml_not_found_by_name(
    client: TestClient,
    access_token: str,
):
    response = client.get(
        "/v1/collections/nonexistent_collection/opds.xml",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    root = ET.fromstring(response.text)
    assert root.tag == f"{{{ATOM_NAMESPACE}}}feed"


def test_get_collection_opds_xml_empty(
    client: TestClient,
    create_collection: Callable[..., Collection],
    access_token: str,
):
    collection = create_collection(name="empty_collection")
    response = client.get(
        f"/v1/collections/{collection.id}/opds.xml",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    root = ET.fromstring(response.text)
    assert root.tag == f"{{{ATOM_NAMESPACE}}}feed"
    assert list(root.findall(f"{{{ATOM_NAMESPACE}}}entry")) == []


def test_get_collection_opds_xml_single_book(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
    illustration_48x48_at_1: str,
    access_token: str,
):
    warehouse = create_warehouse()
    collection = create_collection(warehouse=warehouse)
    title = create_title(name="test_title")

    book = create_book(
        zim_metadata={
            **ZIM_METADATA,
            "Tags": "_category:test;_pictures:no",
            "Illustration_48x48@1": illustration_48x48_at_1,
            "Flavour": "test",
        },
    )
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
        f"/v1/collections/{collection.id}/opds.xml",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == OPDS_MEDIA_TYPE

    expected_etag = xxhash.xxh64(response.content).hexdigest()
    assert response.headers["ETag"] == expected_etag

    root = ET.fromstring(response.text)
    entries = list(root.findall(f"{{{ATOM_NAMESPACE}}}entry"))
    assert len(entries) == 1

    entry = entries[0]
    assert entry.findtext(f"{{{ATOM_NAMESPACE}}}id") == f"urn:uuid:{book.id}"
    assert entry.findtext(f"{{{ATOM_NAMESPACE}}}title") == "Test Title"
    assert entry.findtext(f"{{{ATOM_NAMESPACE}}}summary") == "A test book"
    assert entry.findtext(f"{{{ATOM_NAMESPACE}}}language") == "eng"
    assert (
        entry.findtext(f"{{{ATOM_NAMESPACE}}}author/{{{ATOM_NAMESPACE}}}name")
        == "Test Creator"
    )
    assert (
        entry.findtext(f"{{{ATOM_NAMESPACE}}}publisher/{{{ATOM_NAMESPACE}}}name")
        == "Test Publisher"
    )
    assert entry.findtext(f"{{{ATOM_NAMESPACE}}}updated") == "2025-01-01T00:00:00Z"
    assert entry.findtext(f"{{{DC_NAMESPACE}}}issued") == "2025-01-01T00:00:00Z"
    assert entry.findtext(f"{{{KIWIX_NAMESPACE}}}titleid") == str(title.id)
    assert entry.findtext(f"{{{KIWIX_NAMESPACE}}}popularity") == str(title.popularity)
    assert entry.findtext(f"{{{ATOM_NAMESPACE}}}name") == "test_title"
    assert entry.findtext(f"{{{ATOM_NAMESPACE}}}flavour") == "test"
    assert entry.findtext(f"{{{ATOM_NAMESPACE}}}category") == "test"
    assert entry.findtext(f"{{{ATOM_NAMESPACE}}}tags") == (
        "_category:test;_pictures:no;_ftindex:no;_videos:yes;_details:yes"
    )
    assert entry.findtext(f"{{{ATOM_NAMESPACE}}}articleCount") == str(
        book.article_count
    )
    assert entry.findtext(f"{{{ATOM_NAMESPACE}}}mediaCount") == str(book.media_count)

    links = entry.findall(f"{{{ATOM_NAMESPACE}}}link")
    acquisition_links = {
        link.get("type"): link for link in links if link.get("rel") == ACQUISITION_REL
    }
    assert acquisition_links[ZIM_MIMETYPE].get("href") == (
        "https://download.kiwix.org/zim/wikipedia/test_en_all.zim"
    )
    assert acquisition_links[METALINK_MIMETYPE].get("href") == (
        "https://download.kiwix.org/zim/wikipedia/test_en_all.zim.meta4"
    )
    assert acquisition_links[BITTORRENT_MIMETYPE].get("href") == (
        "https://download.kiwix.org/zim/wikipedia/test_en_all.zim.torrent"
    )
    for link in acquisition_links.values():
        assert link.get("length") == str(book.size)

    thumbnail = next(link for link in links if link.get("rel") == THUMBNAIL_REL)
    assert thumbnail.get("type") == THUMBNAIL_MIMETYPE
    assert thumbnail.get("href") == (
        f"data:{ILLUSTRATION_MIMETYPE};base64,{illustration_48x48_at_1}"
    )


def test_get_collection_opds_xml_illustration_url(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
    illustration_48x48_at_1: str,
    access_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """Illustrations can be referenced by URL instead of being embedded."""
    template = "https://cdn.kiwix.org/books/{book_id}/illustration"
    monkeypatch.setattr("cms_backend.context.Context.opds_inline_illustration", False)
    monkeypatch.setattr(
        "cms_backend.context.Context.opds_illustration_url_template", template
    )

    warehouse = create_warehouse()
    collection = create_collection(warehouse=warehouse)
    title = create_title(name="test_title")
    book = create_book(
        zim_metadata={
            **ZIM_METADATA,
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
    )
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
        f"/v1/collections/{collection.id}/opds.xml",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK

    root = ET.fromstring(response.text)
    entry = next(iter(root.findall(f"{{{ATOM_NAMESPACE}}}entry")))
    thumbnail = next(
        link
        for link in entry.findall(f"{{{ATOM_NAMESPACE}}}link")
        if link.get("rel") == THUMBNAIL_REL
    )
    assert thumbnail.get("href") == template.replace("{book_id}", str(book.id))


def test_get_collection_opds_xml_path_prefix(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
    access_token: str,
):
    """A filesystem path acquisition link is added when path_prefix is given."""
    warehouse = create_warehouse()
    collection = create_collection(warehouse=warehouse)
    title = create_title(name="test_title")
    book = create_book(zim_metadata=dict(ZIM_METADATA))
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
        f"/v1/collections/{collection.id}/opds.xml?path_prefix=/data/dev/",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK

    root = ET.fromstring(response.text)
    entry = next(iter(root.findall(f"{{{ATOM_NAMESPACE}}}entry")))
    hrefs = {
        link.get("href")
        for link in entry.findall(f"{{{ATOM_NAMESPACE}}}link")
        if link.get("rel") == ACQUISITION_REL
    }
    assert "/data/dev/wikipedia/test_en_all.zim" in hrefs


def test_get_staging_opds_xml_empty(
    client: TestClient,
    access_token: str,
):
    response = client.get(
        "/v1/staging/opds.xml", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == HTTPStatus.OK
    root = ET.fromstring(response.text)
    assert root.tag == f"{{{ATOM_NAMESPACE}}}feed"
    assert list(root.findall(f"{{{ATOM_NAMESPACE}}}entry")) == []


def test_get_staging_opds_xml(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    warehouse: Warehouse,
    access_token: str,
):
    collection = create_collection(warehouse=warehouse)
    title = create_title(name="wiki")
    _add_title_to_collection(dbsession, collection, title, "wikipedia")

    book = create_book(zim_metadata={**ZIM_METADATA, "Name": "wiki"})
    book.title = title
    book.needs_processing = False
    book.has_error = False
    book.needs_file_operation = False
    book.location_kind = "staging"
    create_book_location(
        book=book,
        warehouse_id=Context.staging_warehouse_id,
        path=Context.staging_base_path,
        status="current",
        filename="wiki_2025-01.zim",
    )
    dbsession.flush()

    response = client.get(
        "/v1/staging/opds.xml", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == HTTPStatus.OK
    root = ET.fromstring(response.text)
    entries = list(root.findall(f"{{{ATOM_NAMESPACE}}}entry"))
    assert len(entries) == 1
    assert entries[0].findtext(f"{{{ATOM_NAMESPACE}}}id") == f"urn:uuid:{book.id}"
