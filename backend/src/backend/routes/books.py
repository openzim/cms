import base64
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from ormar.exceptions import NoMatch
from zimscraperlib.i18n import find_language_names

from backend import utils
from backend.constants import logger
from backend.event_handlers import ee
from backend.models import (
    BOOK_ONLY_METADATA,
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
from backend.schemas import BookAddSchema, Message
from backend.utils import get_ident_from_name

router = APIRouter(
    prefix="/books",
    tags=["books"],
)


@router.post("/add", status_code=201)
@database.transaction()
async def create_book(book_payload: BookAddSchema):
    """API endpoint to receive Book addition requests and add to database"""

    try:
        title, _ = await Title.objects.get_or_create(
            ident=get_ident_from_name(book_payload.metadata["Name"])
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Name metadata. Unable to build Title identifier: {exc}",
        ) from exc

    if not book_payload.metadata.get("Language"):
        raise HTTPException(
            status_code=400,
            detail="Missing language code",
        )

    book = await Book.objects.create(
        id=book_payload.id,
        counter=book_payload.counter,
        period=book_payload.period,
        article_count=book_payload.article_count,
        media_count=book_payload.media_count,
        size=book_payload.size,
        url=book_payload.url,
        zimcheck=book_payload.zimcheck,
        title=title,
    )
    await ee.emit_async("added_book", book)
    for metadata_name, value in book_payload.metadata.items():
        if metadata_name.startswith("Illustration_"):
            book_metadata = await BookMetadata.objects.create(
                book=book.id,
                name=metadata_name,
                bin_value=base64.standard_b64decode(value),
                kind=KIND_ILLUSTRATION,
            )
        else:
            book_metadata = await BookMetadata.objects.create(
                book=book.id,
                name=metadata_name,
                value=value,
                kind=KIND_TEXT,
            )
        await ee.emit_async(
            "added_book_metadata", book, f"Added {repr(book_metadata)} to {repr(book)}"
        )

    for metadata in await book.metadata.all():
        if metadata.name in BOOK_ONLY_METADATA:
            continue
        if await TitleMetadata.objects.filter(
            title=title.ident, name=metadata.name
        ).exists():
            continue
        title_metadata = await TitleMetadata.objects.create(
            title=title.ident,
            name=metadata.name,
            bin_value=metadata.bin_value,
            value=metadata.value,
            kind=metadata.kind,
        )

        await ee.emit_async(
            "added_title_metadata",
            title,
            f"Added {repr(title_metadata)} to {repr(title)}",
        )
    if book_payload.metadata.get("Tags"):
        for tag_name in book_payload.metadata["Tags"].split(";"):
            book_tag, created = await BookTag.objects.get_or_create(name=tag_name)
            await book.tags.add(book_tag)
            if created:
                await ee.emit_async(
                    "added_book_tag", book, f"Added {repr(book_tag)} to {repr(book)}"
                )
            if not re.match(
                r"_(sw|ftindex|pictures|videos|details):(yes|no)", tag_name
            ):
                title_tag, created = await TitleTag.objects.get_or_create(name=tag_name)
                await title.tags.add(title_tag)
                if created:
                    await ee.emit_async(
                        "added_title_tag",
                        title,
                        f"Added {repr(title_tag)} to {repr(title)}",
                    )
            await book.tags.add(book_tag)

    for lang_code in book_payload.metadata["Language"].split(","):
        native_name, english_name = find_language_names(lang_code)
        language = await Language.get_create_or_update(
            code=lang_code, name=english_name, native=native_name
        )
        await book.languages.add(language)
        await title.languages.add(language)
    flavour = book_payload.metadata.get("Flavour", "")
    try:
        # use via utils.xxx to accomodate monkeypatch in tests
        await utils.remove_obsolete_books(title_ident=title.ident, flavour=flavour)
    except Exception as exc:
        logger.warning(
            f"Unable to remove obsolete books for {title.ident}/{flavour}: {exc}"
        )
        logger.exception(exc)

    return {"uuid": str(book.id), "title": book.title.ident}


@router.get(
    "/{book_id}",
    responses={
        404: {"model": Message, "description": "Requested Book not found"},
        200: {"model": BookAddSchema, "description": "The requested Book"},
    },
)
@database.transaction()
async def get_book(book_id: str):
    try:
        book = await Book.objects.select_all().get(id=book_id)
    except NoMatch:
        return JSONResponse(
            status_code=404, content={"message": f"Book with ID “{book_id}” not found"}
        )

    return {
        "id": book.id,
        "period": book.period,
        "counter": book.counter,
        "article_count": book.article_count,
        "media_count": book.media_count,
        "size": book.size,
        "url": book.url,
        "zimcheck": book.zimcheck,
        "metadata": {
            item.name: (
                base64.standard_b64encode(item.bin_value)
                if item.kind == KIND_ILLUSTRATION
                else item.value
            )
            for item in await book.metadata.all()
        },
    }
