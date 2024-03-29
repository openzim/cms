import base64
import copy
import datetime
import uuid

import pytest
from ormar.exceptions import NoMatch
from utils import clear_book_dict_from

from backend.models import (
    BOOK_ONLY_METADATA,
    KIND_ILLUSTRATION,
    KIND_TEXT,
    Book,
    BookMetadata,
    Language,
    Title,
    TitleMetadata,
)
from backend.utils import get_ident_from_name


@pytest.mark.asyncio
async def test_add_book_create_language(client, book_dict, clear_book_dict):
    response = await client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 201
    assert response.headers.get("Content-Type") == "application/json"

    book = await Book.objects.get(id=book_dict["id"])
    assert response.json() == {
        "uuid": str(book.id),
        "title": book.title.ident,
    }
    assert str(book.id) == book_dict["id"]
    assert book.counter == book_dict["counter"]
    assert book.period == datetime.date.fromisoformat(book_dict["period"])
    assert book.article_count == book_dict["article_count"]
    assert book.size == book_dict["size"]
    assert book.zimcheck == book_dict["zimcheck"]


@pytest.mark.asyncio
async def test_add_book_update_language(
    client, book_dict, clear_book_dict, language_eng
):
    # language_eng is already created in DB but its name and native properties are wrong
    # since they have been updated in Babel
    response = await client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 201
    assert response.headers.get("Content-Type") == "application/json"

    language = await Language.objects.get(code="eng")
    assert language.native == "English (United States)"
    assert language.name == "English (United States)"


@pytest.mark.asyncio
async def test_of_rollback(client, book_dict):
    ident = get_ident_from_name(book_dict["metadata"]["Name"])
    book_dict["metadata"]["Language"] = ""
    response = await client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 400
    assert await Title.objects.filter(ident=ident).count() == 0


@pytest.mark.asyncio
async def test_integrity_error_of_title_metadata(client, book_dict, clear_book_dict):
    response = await client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 201

    book_dict2 = copy.deepcopy(book_dict)
    book_dict2["id"] = str(uuid.uuid4())
    response = await client.post("/v1/books/add", json=book_dict2)
    assert response.status_code == 201
    await clear_book_dict_from(book_dict2["id"], book_dict2["metadata"]["Tags"])


@pytest.mark.asyncio
async def test_add_metadata(client, book_dict, clear_book_dict):
    response = await client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 201
    assert response.headers.get("Content-Type") == "application/json"

    book_metadata = await BookMetadata.objects.fields("id", "metadata").all(
        book=book_dict["id"]
    )
    assert len(book_metadata) == len(book_dict["metadata"])
    for metadata in book_metadata:
        if metadata.name.startswith("Illustration"):
            assert metadata.kind == KIND_ILLUSTRATION
            assert metadata.bin_value == base64.standard_b64decode(
                book_dict["metadata"][metadata.name]
            )
            assert metadata.value == ""
        else:
            assert metadata.kind == KIND_TEXT
            assert metadata.value == book_dict["metadata"][metadata.name]


@pytest.mark.asyncio
async def test_add_book_tags(client, book_dict, clear_book_dict):
    response = await client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 201
    assert response.headers.get("Content-Type") == "application/json"

    book = (
        await Book.objects.select_related("tags")
        .fields("id", "tags")
        .get(id=book_dict["id"])
    )

    assert set(tag.name for tag in book.tags) == set(
        book_dict["metadata"]["Tags"].split(";")
    )


@pytest.mark.asyncio
async def test_save_languages(client, book_dict, clear_book_dict):
    response = await client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 201
    assert response.headers.get("Content-Type") == "application/json"

    book = (
        await Book.objects.select_related("languages")
        .fields("id", "languages")
        .get(id=book_dict["id"])
    )

    assert set(language.code for language in book.languages) == set(
        book_dict["metadata"]["Language"].split(",")
    )

    assert set(language.name for language in book.languages) == set(
        ["Ganda (Uganda)", "Arabic (Egypt)", "English (United States)"]
    )
    assert set(language.native for language in book.languages) == set(
        ["Luganda (Yuganda)", "العربية (مصر)", "English (United States)"]
    )


@pytest.mark.asyncio
async def test_add_title(client, book_dict, clear_book_dict):
    response = await client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 201
    assert response.headers.get("Content-Type") == "application/json"

    book = (
        await Book.objects.select_related("title")
        .fields("id", "title")
        .get(id=book_dict["id"])
    )
    assert book.title is not None
    assert book.title.ident == "wikipedia_lg_all"


@pytest.mark.asyncio
async def test_add_languages(client, book_dict, clear_book_dict):
    response = await client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 201
    assert response.headers.get("Content-Type") == "application/json"

    book = (
        await Book.objects.select_related("title")
        .fields("id", "title")
        .get(id=book_dict["id"])
    )
    title = await Title.objects.select_related("languages").get(ident=book.title.ident)
    assert set(language.name for language in title.languages) == set(
        ["Ganda (Uganda)", "Arabic (Egypt)", "English (United States)"]
    )
    assert set(language.native for language in title.languages) == set(
        ["Luganda (Yuganda)", "العربية (مصر)", "English (United States)"]
    )


@pytest.mark.asyncio
async def test_add_title_tags(client, book_dict, clear_book_dict):
    response = await client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 201
    assert response.headers.get("Content-Type") == "application/json"

    book = (
        await Book.objects.select_related("title")
        .fields("id", "title")
        .get(id=book_dict["id"])
    )
    title = await Title.objects.select_related("tags").get(ident=book.title.ident)
    assert set(tag.name for tag in title.tags) == set(
        ["wikipedia", "_category:wikipedia"]
    )


@pytest.mark.asyncio
async def test_add_title_metadata(client, book_dict, clear_book_dict):
    response = await client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 201
    assert response.headers.get("Content-Type") == "application/json"

    book = (
        await Book.objects.select_related("title")
        .fields("id", "title")
        .get(id=book_dict["id"])
    )

    title_metadata = await TitleMetadata.objects.fields("id", "metadata").all(
        title=book.title.ident
    )
    expected_title_metadata = {
        k: v for k, v in book_dict["metadata"].items() if k not in BOOK_ONLY_METADATA
    }

    assert len(title_metadata) == len(expected_title_metadata)
    for metadata in title_metadata:
        if metadata.name.startswith("Illustration"):
            assert metadata.kind == KIND_ILLUSTRATION
            assert metadata.bin_value == base64.standard_b64decode(
                expected_title_metadata[metadata.name]
            )
            assert metadata.value == ""
        else:
            assert metadata.kind == KIND_TEXT
            assert metadata.value == expected_title_metadata[metadata.name]


@pytest.mark.asyncio
async def test_raise_httpexception_for_incorrect_title(client, book_dict):
    # updating book_dict with incorrect language code
    book_dict["metadata"]["Name"] = "wikipedia_zz_all"
    response = await client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 400
    assert response.headers.get("Content-Type") == "application/json"

    with pytest.raises(NoMatch):
        await Book.objects.get(id=book_dict["id"])

    with pytest.raises(NoMatch):
        await Title.objects.get(ident=book_dict["metadata"]["Name"])


@pytest.mark.asyncio
async def test_get_book_info(client, book_with_metadata, book_dict):
    response = await client.get(f"/v1/books/{book_dict['id']}")
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"

    assert response.json() == book_dict


@pytest.mark.asyncio
async def test_get_book_missing(client):
    response = await client.get("/v1/books/missing")
    assert response.status_code == 404
    assert response.headers.get("Content-Type") == "application/json"

    assert response.json() == {"message": "Book with ID “missing” not found"}


@pytest.mark.asyncio
async def test_get_scraper_name(client, book_with_metadata, book_dict):
    book = await Book.objects.get(id=book_dict["id"])
    assert "mwoffliner 1.11.10" == await book.get_scraper_name()
