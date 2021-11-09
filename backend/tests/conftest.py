import uuid

import pytest

from backend.models import Book, Language, Title, setup


@pytest.fixture(autouse=True, scope="session")
def database_url():
    setup()
    yield


@pytest.fixture(scope="function")
@pytest.mark.asyncio
async def language_eng(book_dict):
    lang = await Language.objects.create(code="eng", name="English", native="English")
    yield lang
    await lang.delete()


@pytest.fixture(scope="function")
@pytest.mark.asyncio
async def language_fra(book_dict):
    lang = await Language.objects.create(code="fra", name="French", native="Français")
    yield lang
    await lang.delete()


@pytest.fixture(scope="function")
def book_dict():
    return {
        "uuid": uuid.uuid4().hex,
        "period": "2021-02-08",
        "counter": {"text/html": 1, "image/png": 1},
        "article_count": 2,
        "media_count": 1,
        "size": 2048,
        "url": "https://mirror.download.kiwix.org/zim/other/test.zim",
        "zimcheck": {
            "zimcheck_version": "3.0.0",
            "checks": [
                "checksum",
                "integrity",
                "empty",
                "metadata",
                "favicon",
                "main_page",
                "redundant",
                "url_internal",
                "url_external",
                "redirect",
            ],
            "file_name": "/output/test.zim",
            "file_uuid": "003b51a2-d0bd-94be-db08-5d58501c10ab",
            "status": True,
            "logs": [],
        },
        "obsolete": False,
    }


@pytest.fixture(scope="function")
@pytest.mark.asyncio
async def book(book_dict):
    book = await Book.objects.create(
        id=book_dict["uuid"],
        counter=book_dict["counter"],
        period=book_dict["period"],
        article_count=book_dict["article_count"],
        media_count=book_dict["media_count"],
        size=book_dict["size"],
        url=book_dict["url"],
        zimcheck=book_dict["zimcheck"],
    )
    yield book
    await book.languages.clear()
    await book.tags.clear()
    await book.metadata.clear()
    await book.delete()


@pytest.fixture(scope="function")
@pytest.mark.asyncio
async def book_with_language(book, language_eng):
    await book.languages.add(language_eng)
    yield book


@pytest.fixture(scope="function")
def title_dict():
    return {
        "ident": "wikipedia_en_test",
    }


@pytest.fixture(scope="function")
@pytest.mark.asyncio
async def title(title_dict):
    title = await Title.objects.create(
        ident=title_dict["ident"],
    )
    yield title
    await title.languages.clear()
    await title.tags.clear()
    await title.metadata.clear()
    await title.delete()


@pytest.fixture(scope="function")
@pytest.mark.asyncio
async def title_with_language(title, language_eng):
    await title.languages.add(language_eng)
    yield title


@pytest.fixture(scope="module")
def base64_png():
    return (
        "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"
    )
