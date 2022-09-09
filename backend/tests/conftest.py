import asyncio
import base64
import pathlib
import uuid

import pytest
import sqlalchemy
from httpx import AsyncClient
from utils import clear_book_dict_from

from backend.main import create_app, shutdown, startup
from backend.models import (
    KIND_ILLUSTRATION,
    KIND_TEXT,
    BaseMeta,
    Book,
    BookMetadata,
    Language,
    Title,
    TitleMetadata,
    TitleTag,
)


@pytest.fixture(autouse=True, scope="session")
def event_loop():
    return asyncio.get_event_loop()


@pytest.fixture(autouse=True, scope="session")
def app():
    return create_app()


@pytest.fixture(autouse=True, scope="session")
async def test_database():
    engine = sqlalchemy.create_engine(str(BaseMeta.database.url))
    BaseMeta.metadata.drop_all(engine)  # reset db first
    BaseMeta.metadata.create_all(engine)
    await startup()
    yield
    await shutdown()
    BaseMeta.metadata.drop_all(engine)


@pytest.fixture(scope="session")
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
async def clear_titles():
    yield
    await Title.objects.delete(each=True)


@pytest.fixture(scope="function")
async def clear_title_tags():
    yield
    await TitleTag.objects.delete(each=True)


@pytest.fixture(scope="function")
async def clear_book_dict(book_dict):
    """removes metadata, tags, languages, title and book created from the book_dict"""
    yield
    await clear_book_dict_from(book_dict["id"], book_dict["metadata"]["Tags"])


@pytest.fixture(scope="function")
async def language_eng():
    lang = await Language.objects.create(code="eng", name="English", native="English")
    yield lang
    await lang.delete()


@pytest.fixture(scope="function")
async def language_fra():
    lang = await Language.objects.create(code="fra", name="French", native="Français")
    yield lang
    await lang.delete()


@pytest.fixture(scope="function")
async def language_lug():
    lang = await Language.objects.create(
        code="lug", name="Ganda (Uganda)", native="Luganda (Yuganda)"
    )
    yield lang
    await lang.delete()


@pytest.fixture(scope="function")
async def language_ara():
    lang = await Language.objects.create(
        code="ara", name="Arabic (Egypt)", native="العربية (مصر)"
    )
    yield lang
    await lang.delete()


@pytest.fixture(scope="function")
def book_dict(base64_png):
    return {
        "id": str(uuid.uuid4()),
        "period": "2021-02-08",
        "counter": {"text/html": 1, "image/png": 1},
        "article_count": 2,
        "media_count": 1,
        "size": 2048,
        "url": "https://mirror.download.kiwix.org/zim/other/test.zim",
        "metadata": {
            "Counter": "text/plain=10;text/css=22;application/javascript=23;"
            "image/png=1;text/html=2567;image/webp=719;image/svg+xml;"
            " charset=utf-8; "
            'profile="https://www.mediawiki.org/wiki/Specs/SVG/1.0.0"=1',
            "Creator": "Wikipedia",
            "Date": "2021-11-05",
            "Description": "offline version of Wikipedia in Ganda",
            "Flavour": "maxi",
            "Language": "lug,eng,ara",
            "Name": "wikipedia_lg_all",
            "Publisher": "Kiwix",
            "Scraper": "mwoffliner 1.11.10",
            "Tags": "wikipedia;_category:wikipedia;_pictures:yes;"
            "_videos:no;_details:yes;_ftindex:yes",
            "Title": "Wikipedia",
            "Illustration_48x48": base64_png,
        },
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
    }


@pytest.fixture(scope="function")
async def book(book_dict):
    book = await Book.objects.create(
        id=book_dict["id"],
        counter=book_dict["counter"],
        period=book_dict["period"],
        article_count=book_dict["article_count"],
        media_count=book_dict["media_count"],
        size=book_dict["size"],
        url=book_dict["url"],
        zimcheck=book_dict["zimcheck"],
    )
    yield book
    await book.languages.clear(keep_reversed=False)
    await book.tags.clear()
    await book.metadata.clear(keep_reversed=False)
    await book.delete()


@pytest.fixture(scope="function")
async def book_with_language(book, language_eng):
    await book.languages.add(language_eng)
    yield book


@pytest.fixture(scope="function")
async def book_with_metadata(book, book_dict):
    for metadata_name, value in book_dict["metadata"].items():
        if metadata_name.startswith("Illustration_"):
            await BookMetadata.objects.create(
                book=book.id,
                name=metadata_name,
                bin_value=base64.standard_b64decode(value),
                kind=KIND_ILLUSTRATION,
            )
        else:
            await BookMetadata.objects.create(
                book=book.id,
                name=metadata_name,
                value=value,
                kind=KIND_TEXT,
            )
    yield book
    await book.metadata.clear(keep_reversed=False)


@pytest.fixture(scope="function")
def title_dict():
    return {
        "ident": "wikipedia_en_test",
    }


@pytest.fixture(scope="function")
async def title(title_dict):
    title = await Title.objects.create(
        ident=title_dict["ident"],
    )
    yield title
    await title.languages.clear(keep_reversed=False)
    await title.tags.clear()
    await title.metadata.clear(keep_reversed=False)
    await title.delete()


@pytest.fixture(scope="function")
async def title_with_language(title, language_eng):
    await title.languages.add(language_eng)
    yield title


@pytest.fixture(scope="function")
async def title_tag():
    tag = await TitleTag.objects.create(name="wikipedia")
    yield tag
    await tag.delete()


@pytest.fixture(scope="function")
async def title_with_data(
    title,
    language_eng,
    language_lug,
    language_ara,
    title_tag,
    book_dict,
    book_with_metadata,
):
    await title.languages.add(language_lug)
    await title.languages.add(language_eng)
    await title.languages.add(language_ara)

    category_tag = await TitleTag.objects.create(name="_category:wikipedia")
    await title.tags.add(title_tag)
    await title.tags.add(category_tag)

    # using book_dict to add metadata to the title, for testing
    for metadata_name, value in book_dict["metadata"].items():
        if metadata_name.startswith("Illustration_"):
            await TitleMetadata.objects.create(
                title=title.ident,
                name=metadata_name,
                bin_value=base64.standard_b64decode(value),
                kind=KIND_ILLUSTRATION,
            )
        else:
            await TitleMetadata.objects.create(
                title=title.ident,
                name=metadata_name,
                value=value,
                kind=KIND_TEXT,
            )
    await title.books.add(book_with_metadata)
    yield title
    await title.languages.clear(keep_reversed=False)
    await title.tags.clear(keep_reversed=False)
    await title.metadata.clear(keep_reversed=False)
    await title.books.clear()
    await title.delete()
    await category_tag.delete()


@pytest.fixture(scope="session")
def ssh_private_key(tmpdir_factory):
    fpath = pathlib.Path(tmpdir_factory.mktemp("data")) / "test_key"
    with open(fpath, "w") as f:
        f.write(
            "-----BEGIN OPENSSH PRIVATE KEY-----"
            "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAArAAAABNlY2RzYS"
            "1zaGEyLW5pc3RwNTIxAAAACG5pc3RwNTIxAAAAhQQBdd7LkqFrRhjNRFaJdH69EegPzUrD"
            "q0nBs33C0PGrWfOq6SzpmpCLrLUmky6fBVSluCEyfgFKuf4q8ev5k1eNcTMAeZ6i0uGBYq"
            "r7wfTWlQNRrtJq/hsDWnfvu+UX7gO0jGA9IvRuS/T1AyWqwm8M7MgxSVfHp8RCQIYEyzGX"
            "cY7Z1KIAAAEQmJUd+JiVHfgAAAATZWNkc2Etc2hhMi1uaXN0cDUyMQAAAAhuaXN0cDUyMQ"
            "AAAIUEAXXey5Kha0YYzURWiXR+vRHoD81Kw6tJwbN9wtDxq1nzquks6ZqQi6y1JpMunwVU"
            "pbghMn4BSrn+KvHr+ZNXjXEzAHmeotLhgWKq+8H01pUDUa7Sav4bA1p377vlF+4DtIxgPS"
            "L0bkv09QMlqsJvDOzIMUlXx6fEQkCGBMsxl3GO2dSiAAAAQgFLU9fztUffe7jp+nuo30wA"
            "0/ABOGCvSz9/GI8FGXJ073fenbK8nOjO6X6sGKhj76ANkXcqpA/MlxpjkkT+A6YwrwAAAB"
            "BmYWRAZmFkaWdhLmxvY2FsAQI="
            "-----END OPENSSH PRIVATE KEY-----"
        )
    return fpath


@pytest.fixture(scope="module")
def base64_png():
    return (
        "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"
    )


@pytest.fixture(scope="function")
def title_ara_dict():
    return {
        "ident": "wikipedia_ar_all",
    }


@pytest.fixture(scope="function")
@pytest.mark.asyncio
async def title_ara(title_ara_dict, language_ara):
    title = await Title.objects.create(
        ident=title_ara_dict["ident"],
    )
    await title.languages.add(language_ara)
    yield title
    await title.languages.clear(keep_reversed=False)
    await title.tags.clear()
    await title.metadata.clear(keep_reversed=False)
    await title.delete()


@pytest.fixture(scope="function")
def title_fra_dict():
    return {
        "ident": "wikipedia_fr_all",
    }


@pytest.fixture(scope="function")
@pytest.mark.asyncio
async def title_fra(title_fra_dict, language_fra):
    title = await Title.objects.create(
        ident=title_fra_dict["ident"],
    )
    await title.languages.add(language_fra)
    yield title
    await title.languages.clear(keep_reversed=False)
    await title.tags.clear()
    await title.metadata.clear(keep_reversed=False)
    await title.delete()


@pytest.fixture(scope="function")
def title_fra_eng_dict():
    return {
        "ident": "wikipedia_fr-eng_nopic",
    }


@pytest.fixture(scope="function")
@pytest.mark.asyncio
async def title_fra_eng(title_fra_eng_dict, language_fra, language_eng):
    title = await Title.objects.create(
        ident=title_fra_eng_dict["ident"],
    )
    await title.languages.add(language_fra)
    await title.languages.add(language_eng)
    yield title
    await title.languages.clear(keep_reversed=False)
    await title.tags.clear()
    await title.metadata.clear(keep_reversed=False)
    await title.delete()


@pytest.fixture(scope="function")
@pytest.mark.asyncio
async def titles_with_metadata(language_fra, language_eng):
    title_fra = await Title.objects.create(ident="wikipedia_fr_all")
    await title_fra.languages.add(language_fra)
    await title_fra.tags.add(
        (await TitleTag.objects.get_or_create(name="wikipedia"))[0]
    )
    await title_fra.tags.add(
        (await TitleTag.objects.get_or_create(name="_category:wikipedia"))[0]
    )
    await title_fra.tags.add((await TitleTag.objects.get_or_create(name="french"))[0])
    await TitleMetadata.objects.create(
        name="Name", kind=KIND_TEXT, value="wikipedia_fr_all", title=title_fra.ident
    )
    await TitleMetadata.objects.create(
        name="Scraper", kind=KIND_TEXT, value="mwoffliner", title=title_fra.ident
    )

    title_eng = await Title.objects.create(ident="wikipedia_en_all")
    await title_eng.languages.add(language_eng)
    await title_eng.tags.add(
        (await TitleTag.objects.get_or_create(name="_category:wikipedia"))[0]
    )
    await title_eng.tags.add(
        (await TitleTag.objects.get_or_create(name="wikipedia"))[0]
    )
    await title_eng.tags.add((await TitleTag.objects.get_or_create(name="english"))[0])
    await TitleMetadata.objects.create(
        name="Name", kind=KIND_TEXT, value="wikipedia_en_all", title=title_eng.ident
    )
    await TitleMetadata.objects.create(
        name="Scraper", kind=KIND_TEXT, value="mwoffliner", title=title_eng.ident
    )

    yield
    for title in (title_fra, title_eng):
        await title.languages.clear(keep_reversed=False)
        for tag in await title.tags.all():
            await tag.delete()
        await title.tags.clear()
        await title.metadata.clear(keep_reversed=False)
        for metadata in await title.metadata.all():
            await metadata.delete()
        await title.delete()


@pytest.fixture(scope="function")
@pytest.mark.asyncio
async def titles_with_metadata_books(client, book_dict):

    ids = []
    book_dict["metadata"]["Name"] = "wikipedia_en_all"
    book_dict["metadata"]["Flavour"] = "maxi"
    book_dict["metadata"]["Language"] = "eng"
    ids.append(book_dict["id"])
    await client.post("/v1/books/add", json=book_dict)

    book_dict["metadata"]["Name"] = "wikipedia_fr_all"
    book_dict["metadata"]["Language"] = "fra"
    del book_dict["metadata"]["Flavour"]
    book_dict["id"] = str(uuid.uuid4())
    ids.append(book_dict["id"])
    await client.post("/v1/books/add", json=book_dict)

    yield

    for bid in ids:
        await clear_book_dict_from(bid, book_dict["metadata"]["Tags"])


@pytest.fixture(scope="function")
@pytest.mark.asyncio
async def title_with_three_books(client, book_dict):

    title = await Title.objects.create(ident="wikipedia_ar_mathematics")
    ids = []
    for period in ["2021-04-08", "2021-05-08", "2021-06-08"]:
        id_ = str(uuid.uuid4())
        await Book.objects.create(
            id=id_,
            counter=book_dict["counter"],
            period=period,
            article_count=book_dict["article_count"],
            media_count=book_dict["media_count"],
            size=book_dict["size"],
            url=book_dict["url"],
            zimcheck={},
            title=title,
        )
        ids.append(id_)

    yield

    for bid in ids:
        if await Book.objects.filter(id=bid).exists():
            await clear_book_dict_from(bid, book_dict["metadata"]["Tags"])
