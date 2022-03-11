import base64
import datetime

import pytest

from backend.models import (
    KIND_ILLUSTRATION,
    KIND_TEXT,
    Book,
    BookMetadata,
    BookTag,
    Language,
    Title,
    TitleMetadata,
    TitleTag,
    get_matched_m2m_combination,
    matching_metadata,
    reduce_qs,
    star_to_like,
)


@pytest.mark.asyncio
async def test_language():
    assert await Language.objects.count() == 0
    lang = await Language.objects.create(code="bam", name="Bamanakan", native="Bambara")
    assert lang.code == "bam"
    assert lang.name == "Bamanakan"
    assert lang.native == "Bambara"
    with pytest.raises(Exception):
        await Language.objects.create(code="bam", name="Bamanakan", native="Bambara")
    await lang.delete()


######
# Book CRUD
######
@pytest.mark.asyncio
async def test_book_create(book_dict, clear_book_dict):
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
    assert str(book.id) == book_dict["id"]
    assert book.counter == book_dict["counter"]
    assert book.period == datetime.date.fromisoformat(book_dict["period"])
    assert book.article_count == book_dict["article_count"]
    assert book.size == book_dict["size"]
    assert book.zimcheck == book_dict["zimcheck"]
    assert await book.book_name() == ""


@pytest.mark.asyncio
async def test_book_update(book):
    initial_period = str(book.period)
    book.period = book.period + datetime.timedelta(days=1)
    await book.update()
    book = await Book.objects.get(id=book.id)
    assert str(book.period) != initial_period


@pytest.mark.asyncio
async def test_book_delete(book):
    id_ = book.id
    assert await Book.objects.filter(id=id_).count() == 1
    await book.delete()
    assert await Book.objects.filter(id=id_).count() == 0


@pytest.mark.asyncio
async def test_book_languages(book_with_language, language_fra):
    assert await book_with_language.languages.count() == 1
    assert (await book_with_language.language).code == "eng"
    await book_with_language.languages.add(language_fra)
    assert await book_with_language.languages.count() == 2
    await book_with_language.languages.clear(keep_reversed=False)
    assert await book_with_language.languages.count() == 0


@pytest.mark.asyncio
async def test_book_tag_create():
    tag = await BookTag.objects.create(name="wikipedia")
    assert not tag.private
    tag = await BookTag.objects.create(name="_sw:yes")
    assert tag.private
    assert await BookTag.objects.count() == 2

    await BookTag.objects.delete(name="wikipedia")
    await BookTag.objects.delete(name="_sw:yes")


@pytest.mark.asyncio
async def test_book_metadata(book):
    metadata = {"Scraper": "mwoffliner 1.0", "Title": "Test title"}
    for name, value in metadata.items():
        await BookMetadata.objects.create(
            book=book, name=name, kind=KIND_TEXT, value=value
        )
    assert await book.metadata.count() == len(metadata.keys())


@pytest.mark.asyncio
async def test_book_illustrations(book, base64_png):
    image = base64.standard_b64decode(base64_png)
    await BookMetadata.objects.create(
        book=book, name="Illustration_48x48", kind=KIND_ILLUSTRATION, bin_value=image
    )
    assert await book.illustrations.count() == 1
    assert (await book.illustration).size == 48
    assert await book.get_illustration() == image


######
# Title CRUD
######
@pytest.mark.asyncio
async def test_title_create(clear_titles):
    ident = "wikipedia_bm_test"
    title = await Title.objects.create(
        ident=ident,
    )
    assert title.ident == ident


@pytest.mark.asyncio
async def test_title_delete(title):
    ident = str(title.ident)
    assert await Title.objects.filter(ident=ident).count() == 1
    await title.delete()
    assert await Title.objects.filter(ident=ident).count() == 0


@pytest.mark.asyncio
async def test_title_languages(title_with_language, language_fra):
    assert await title_with_language.languages.count() == 1
    assert (await title_with_language.language).code == "eng"
    await title_with_language.languages.add(language_fra)
    assert await title_with_language.languages.count() == 2
    await title_with_language.languages.clear(keep_reversed=False)
    assert await title_with_language.languages.count() == 0


@pytest.mark.asyncio
async def test_title_tag_create(clear_title_tags):
    tag = await TitleTag.objects.create(name="wikipedia")
    assert not tag.private
    tag = await TitleTag.objects.create(name="_sw:yes")
    assert tag.private
    assert await TitleTag.objects.count() == 2


@pytest.mark.asyncio
async def test_title_metadata(title):
    metadata = {"Scraper": "mwoffliner 1.0", "Title": "Test title"}
    for name, value in metadata.items():
        await TitleMetadata.objects.create(
            title=title, name=name, kind=KIND_TEXT, value=value
        )
    assert await title.metadata.count() == len(metadata.keys())
    meta = await title.metadata.first()
    assert meta.size is None


@pytest.mark.asyncio
async def test_title_illustrations(title, base64_png):
    image = base64.standard_b64decode(base64_png)
    await TitleMetadata.objects.create(
        title=title, name="Illustration_48x48", kind=KIND_ILLUSTRATION, bin_value=image
    )
    assert await title.illustrations.count() == 1
    assert (await title.illustration).size == 48
    assert await title.get_illustration() == image

    # insert bad illustration (incorrect name)
    illus = await TitleMetadata.objects.create(
        title=title, name="Illustration_96", kind=KIND_ILLUSTRATION, bin_value=image
    )
    # `.illustrations` is dumb and just checks for begining of Name
    assert await title.illustrations.count() == 2
    assert illus.size is None


@pytest.mark.asyncio
async def test_get_matched_m2m_combination(title_fra_eng):
    assert (
        len(
            await get_matched_m2m_combination(items=["eng", "fra"], on="title-language")
        )
        == 1
    )

    with pytest.raises(ValueError, match="Invalid"):
        await get_matched_m2m_combination(
            items=["eng", "fra"], on="title-erp", combination="intersection"
        )
    with pytest.raises(ValueError, match="Invalid"):
        await get_matched_m2m_combination(
            items=["eng", "fra"], on="erp-language", combination="intersection"
        )
    with pytest.raises(ValueError, match="Invalid"):
        await get_matched_m2m_combination(
            items=["eng", "fra"], on="title-language", combination="erp"
        )


def test_star_to_like():
    assert star_to_like("wikipedia_*_all") == "wikipedia_%_all"
    assert star_to_like("wikipedia*") == "wikipedia%"
    assert star_to_like("*_all") == "%_all"
    assert star_to_like("wikipedia*_a*") == "wikipedia%_a%"
    assert star_to_like("wikipedia_%_all") == "wikipedia_\\%_all"


@pytest.mark.asyncio
async def test_reduce_qs(title, title_fra_eng):
    qs = Title.objects
    assert await reduce_qs(qs) == [title.ident, title_fra_eng.ident]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name, value, expected, using",
    [
        ("Name", "wikipedia_fr_all", ["wikipedia_fr_all"], None),
        ("Name", "wikipedia_en_all", ["wikipedia_en_all"], None),
        ("Scraper", "mwoffliner", ["wikipedia_en_all", "wikipedia_fr_all"], None),
        ("Name", "wikipedia_fr_all", ["wikipedia_fr_all"], ["wikipedia_fr_all"]),
        ("Name", "wikipedia_en_all", [], ["wikipedia_fr_all"]),
        ("Scraper", "mwoffliner", ["wikipedia_fr_all"], ["wikipedia_fr_all"]),
    ],
)
async def test_matching_metadata(titles_with_metadata, name, value, expected, using):
    # idents = [title.ident, title_fra_eng.ident]
    assert (
        await matching_metadata(
            on="title",
            name=name,
            value=star_to_like(value),
            using=using,
        )
        == expected
    )
