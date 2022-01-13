import base64
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from ormar.exceptions import NoMatch
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
from backend.schemas import BookAddSchema, Message
from backend.utils import get_ident_from_name

router = APIRouter(
    prefix="/books",
    tags=["books"],
)


@database.transaction()
@router.post("/add", status_code=201)
async def create_book(book_payload: BookAddSchema):
    """API endpoint to receive Book addition requests and add to database"""

    try:
        title = await Title.objects.get_or_create(
            ident=get_ident_from_name(book_payload.metadata["Name"])
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Name metadata. Unable to build Title identifier: {exc}",
        ) from exc

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

    for metadata_name, value in book_payload.metadata.items():
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

    for metadata in await book.metadata.all():
        await TitleMetadata.objects.create(
            title=title.ident,
            name=metadata.name,
            bin_value=metadata.bin_value,
            value=metadata.value,
            kind=metadata.kind,
        )

    for tag_name in book_payload.metadata["Tags"].split(";"):
        book_tag = await BookTag.objects.get_or_create(name=tag_name)
        await book.tags.add(book_tag)
        if not re.match(r"_(sw|ftindex|pictures|videos|details):(yes|no)", tag_name):
            title_tag = await TitleTag.objects.get_or_create(name=tag_name)
            await title.tags.add(title_tag)

    for lang_code in book_payload.metadata["Language"].split(","):
        native_name, english_name = find_language_names(lang_code)
        language = await Language.objects.get_or_create(
            code=lang_code, name=english_name, native=native_name
        )
        await book.languages.add(language)
        await title.languages.add(language)

    return {"msg": "ok", "uuid": str(book.id), "title": book.title.ident}


@database.transaction()
@router.get(
    "/{id}",
    responses={
        404: {"model": Message, "description": "Requested Title not found"},
        200: {"model": BookAddSchema, "description": "The requested Title"},
    },
)
async def get_book(id: str):
    try:
        book = await Book.objects.select_all().get(id=id)
    except NoMatch:
        return JSONResponse(
            status_code=404, content={"message": f"Title with ID “{id}” not found"}
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
