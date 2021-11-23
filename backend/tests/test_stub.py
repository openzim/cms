import base64
import datetime
import math

import pytest
from fastapi.testclient import TestClient

import backend
from backend.main import PREFIX, app
from backend.models import KIND_ILLUSTRATION, KIND_TEXT, Book, BookMetadata

client = TestClient(app)


def test_metadata():
    assert backend.__version__
    assert backend.__title__
    assert backend.__description__


def test_root():
    response = client.get("/", allow_redirects=False)
    assert response.status_code == 308
    response = client.get("/", allow_redirects=True)
    assert response.url.endswith(PREFIX + "/")
    assert response.headers.get("Content-Type") == "application/json"
    assert response.json() == "Hello World"


def test_test_endpoint():
    now = datetime.datetime.now()
    timestamp = math.ceil(now.timestamp())
    response = client.get(f"/v1/test/{timestamp}")
    assert response.status_code == 200
    data = response.json()
    for key in ("requested_on", "received_on"):
        assert isinstance(data.get(key), str)
        assert datetime.datetime.fromisoformat(data.get(key)) >= now


def test_test_endpoint_missing_input():
    response = client.get("/v1/test/")
    assert response.status_code == 404


def test_test_endpoint_invalid_input():
    for param in ("allo", 1000000000000):
        response = client.get(f"/v1/test/{param}")
        assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_books_add_endpoint(book_dict, base64_png):
    book_dict["metadata"]["Illustration_48x48"] = base64_png
    response = client.post("/v1/books/add/", json=book_dict)
    assert response.status_code == 201
    assert response.headers.get("Content-Type") == "application/json"

    book = await Book.objects.get(id=book_dict["id"])
    assert str(book.id) == book_dict["id"]
    assert book.counter == book_dict["counter"]
    assert book.period == datetime.date.fromisoformat(book_dict["period"])
    assert book.article_count == book_dict["article_count"]
    assert book.size == book_dict["size"]
    assert book.zimcheck == book_dict["zimcheck"]


@pytest.mark.asyncio
async def test_books_add_endpoint_save_book_metadata(book_dict, base64_png):
    book_dict["metadata"]["Illustration_48x48"] = base64_png
    response = client.post("/v1/books/add/", json=book_dict)
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
async def test_books_add_endpoint_save_book_tags(book_dict, base64_png):
    book_dict["metadata"]["Illustration_48x48"] = base64_png
    response = client.post("/v1/books/add/", json=book_dict)
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
async def test_books_add_endpoint_save_languages(book_dict, base64_png):
    book_dict["metadata"]["Illustration_48x48"] = base64_png
    response = client.post("/v1/books/add/", json=book_dict)
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
