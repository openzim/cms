import asyncio
import base64
import re
import uuid

from zimscraperlib.i18n import find_language_names

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
    database,
)


@database.transaction()
async def load_fixture():

    lang_codes = [
        "lg",
        "hi",
        "zh",
        "en",
        "fr",
        "de",
        "gu",
        "lt",
        "ml",
        "no",
        "ko",
        "la",
        "sa",
    ]

    base64_png = (
        "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"
    )

    book_dict = {
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
            "Language": "lug",
            "Name": "wikipedia_lg_all",
            "Publisher": "Kiwix",
            "Scraper": "mwoffliner 1.11.10",
            "Tags": "wikipedia;_category:wikipedia;_pictures:yes;"
            "_videos:no;_details:yes;_ftindex:yes",
            "Title": "Wikipedia",
            "Illustration_48x48": (base64_png),
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

    titles = []
    for lang_code in lang_codes:
        title = await Title.objects.create(ident=f"wikipedia_{lang_code}_all")
        titles.append(title)

        book = await Book.objects.create(
            id=str(uuid.uuid4()),
            counter=book_dict["counter"],
            period=book_dict["period"],
            article_count=book_dict["article_count"],
            media_count=book_dict["media_count"],
            size=book_dict["size"],
            url=book_dict["url"],
            zimcheck=book_dict["zimcheck"],
            title=title,
        )

        # create Languages, and add to the Book and Title
        native_name, english_name = find_language_names(lang_code)
        language = await Language.objects.get_or_create(
            code=lang_code, name=english_name, native=native_name
        )
        await book.languages.add(language)
        await title.languages.add(language)

        # add metadata to the Book
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
        # use Book MEtadata to add to the Title
        for metadata in await book.metadata.all():
            await TitleMetadata.objects.create(
                title=title.ident,
                name=metadata.name,
                bin_value=metadata.bin_value,
                value=metadata.value,
                kind=metadata.kind,
            )

        # add tags
        for tag_name in book_dict["metadata"]["Tags"].split(";"):
            book_tag = await BookTag.objects.get_or_create(name=tag_name)
            await book.tags.add(book_tag)
            if not re.match(
                r"_(sw|ftindex|pictures|videos|details):(yes|no)", tag_name
            ):
                title_tag = await TitleTag.objects.get_or_create(name=tag_name)
                await title.tags.add(title_tag)

    # add multiple books to a title
    for _ in range(3):
        await Book.objects.create(
            id=str(uuid.uuid4()),
            counter=book_dict["counter"],
            period=book_dict["period"],
            article_count=book_dict["article_count"],
            media_count=book_dict["media_count"],
            size=book_dict["size"],
            url=book_dict["url"],
            zimcheck=book_dict["zimcheck"],
            title=titles[1],
        )

    print(f"Database URL: {database.url}")
    print(await Book.objects.filter().count(), "books")
    print(await Title.objects.filter().count(), "titles")
    print(await Language.objects.filter().count(), "languages")
    print(await TitleTag.objects.filter().count(), "TitleTags")
    print(await BookTag.objects.filter().count(), "BookTags")


asyncio.run(load_fixture())
