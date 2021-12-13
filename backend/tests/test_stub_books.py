import base64
import datetime

import pytest
from fastapi.testclient import TestClient
from ormar.exceptions import NoMatch

from backend.main import app
from backend.models import (
    KIND_ILLUSTRATION,
    KIND_TEXT,
    Book,
    BookMetadata,
    Title,
    TitleMetadata,
)

client = TestClient(app)


@pytest.mark.asyncio
async def test_books_add_endpoint(book_dict):
    await TitleMetadata.objects.delete(title=book_dict["metadata"]["Name"])
    response = client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 201
    assert response.headers.get("Content-Type") == "application/json"

    book = await Book.objects.get(id=book_dict["id"])
    assert response.json() == {
        "msg": "ok",
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
async def test_books_add_endpoint_save_book_metadata(book_dict):
    await TitleMetadata.objects.delete(title=book_dict["metadata"]["Name"])
    response = client.post("/v1/books/add", json=book_dict)
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
async def test_books_add_endpoint_save_book_tags(book_dict):
    await TitleMetadata.objects.delete(title=book_dict["metadata"]["Name"])
    response = client.post("/v1/books/add", json=book_dict)
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
async def test_books_add_endpoint_save_languages(book_dict):
    await TitleMetadata.objects.delete(title=book_dict["metadata"]["Name"])
    response = client.post("/v1/books/add", json=book_dict)
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
async def test_books_title(book_dict):
    await TitleMetadata.objects.delete(title=book_dict["metadata"]["Name"])
    response = client.post("/v1/books/add", json=book_dict)
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
async def test_books_title_save_languages(book_dict):
    await TitleMetadata.objects.delete(title=book_dict["metadata"]["Name"])
    response = client.post("/v1/books/add", json=book_dict)
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
async def test_books_title_save_tags(book_dict):
    await TitleMetadata.objects.delete(title=book_dict["metadata"]["Name"])
    response = client.post("/v1/books/add", json=book_dict)
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
async def test_books_title_save_metadata(book_dict):
    await TitleMetadata.objects.delete(title=book_dict["metadata"]["Name"])
    response = client.post("/v1/books/add", json=book_dict)
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

    assert len(title_metadata) == len(book_dict["metadata"])
    for metadata in title_metadata:
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
async def test_books_title_raise_httpexception_for_title(book_dict):
    # updating book_dict with incorrect language code
    book_dict["metadata"]["Name"] = "wikipedia_zz_all"
    await TitleMetadata.objects.delete(title=book_dict["metadata"]["Name"])
    response = client.post("/v1/books/add", json=book_dict)
    assert response.status_code == 400
    assert response.headers.get("Content-Type") == "application/json"

    with pytest.raises(NoMatch):
        await Book.objects.get(id=book_dict["id"])

    with pytest.raises(NoMatch):
        await Title.objects.get(ident=book_dict["metadata"]["Name"])