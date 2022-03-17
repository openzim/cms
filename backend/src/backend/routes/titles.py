import base64
import http
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi_pagination import Page, Params, paginate
from ormar.exceptions import NoMatch
from sqlalchemy import select

from backend.models import (
    KIND_ILLUSTRATION,
    KIND_TEXT,
    Title,
    database,
    get_matched_m2m_combination,
    matching_metadata,
    reduce_qs,
    star_to_like,
)
from backend.schemas import Message, TitleSendSchema, TitlesListSendSchemasHolder

router = APIRouter(
    prefix="/titles",
    tags=["titles"],
)


@database.transaction()
@router.get(
    "",
    status_code=200,
    tags=["titles"],
    responses={
        200: {
            "model": Page[Union[TitlesListSendSchemasHolder.all()]],
            "description": "Titles list",
        },
    },
)
async def list_titles(
    params: Params = Depends(),
    ident: str = Query(
        None,
        title="Ident lookup query",
        description="Ident to match results against. "
        "Can include `*` which matches anything (multi chars).",
    ),
    lang: str = Query(
        None,
        title="Language matching query",
        description="ISO-639-3 language codes to filter Titles by. "
        "Multiple-language queries must use either `|` for union of language matches "
        "or `,` for intersection.",
        min_length=3,
        regex=r"[a-z,\,|]{3,}",
    ),
    tag: str = Query(
        None,
        title="Tag matching query",
        description="Tags to filter Titles by."
        "Multiple-tag queries must use either `|` for union of tag matches "
        "or `,` for intersection.",
    ),
    metadata: Optional[List[str]] = Query(
        None,
        title="Metadata query",
        description="List of single `{name}:{value}` metadata query. "
        "All metadata queries are combined (intersection). "
        "Value can include `*` which matches anything (multi chars).",
    ),
    with_languages: bool = Query(
        False,
        alias="with-languages",
        title="Include Languages in response.",
        description="Whether to include the `languages` list for each returned Title.",
    ),
    with_tags: bool = Query(
        False,
        alias="with-tags",
        title="Include Tags in response.",
        description="Whether to include the `tags` list for each returned Title.",
    ),
    with_metadata: Optional[List[str]] = Query(
        None,
        alias="with-metadata",
        title="Included Metadata in response.",
        description="Which (if any – default is none) Metadata to include "
        "in the `metadata` dict for each returned Title (not included if none). "
        "Single-value of `all` or `true` includes them all. Single-value of `all-text` "
        "includes all text metadata (excludes binaries and illustrations)",
    ),
):
    qs = Title.objects.prefetch_related(["languages", "tags", "metadata"])

    # filter on ident lookup. Usage of `*` is expected
    if ident:
        stmt = select(Title.Meta.table.c.ident).where(
            Title.Meta.table.c.ident.like(star_to_like(ident))
        )
        qs = qs.filter(ident__in=[row[0] for row in await database.fetch_all(stmt)])

    # filter on language code of Titles
    # intersection (comma separated) or union (pipe separated)
    if lang:
        # invalid combination of operators
        if "," in lang and "|" in lang:
            raise HTTPException(
                status_code=http.HTTPStatus.BAD_REQUEST,
                detail="`lang` parameter cannot mix intersection and union. "
                "Use either `,` or `|`.",
            )
        # intersection of languages
        if "," in lang:
            qs = qs.filter(
                ident__in=await get_matched_m2m_combination(
                    items=lang.split(","),
                    on="title-language",
                    combination="intersection",
                )
            )
        # Applies to both single values of union of | seperated values
        else:
            qs = qs.filter(
                ident__in=await get_matched_m2m_combination(
                    items=lang.split("|"), on="title-language", combination="union"
                )
            )

    # filter on tag
    if tag:
        # invalid combination of operators
        if "," in tag and "|" in tag:
            raise HTTPException(
                status_code=http.HTTPStatus.BAD_REQUEST,
                detail="`tag` parameter cannot mix intersection and union. "
                "Use either `,` or `|`.",
            )
        # intersection of tags
        if "," in tag:
            qs = qs.filter(
                ident__in=await get_matched_m2m_combination(
                    items=tag.split(","),
                    on="title-titletag",
                    combination="intersection",
                )
            )
        # Applies to both single values of union of | seperated values
        else:
            qs = qs.filter(
                ident__in=await get_matched_m2m_combination(
                    items=tag.split("|"), on="title-titletag", combination="union"
                )
            )

    # filter on metadata
    if metadata:
        idents = await reduce_qs(qs) or None
        for name, value in [line.split(":", 1) for line in metadata]:
            idents = await matching_metadata(
                on="title",
                name=name,
                value=star_to_like(value),
                using=idents,
            )
        qs = qs.filter(ident__in=idents)

    def dress_page(page):
        """transform items from Title model to appropriate schema based on request"""

        def text_only_filter(item):
            return item.kind == KIND_TEXT

        def passed_metadata_filter(item):
            return item.name.lower() in [meta.strip().lower() for meta in with_metadata]

        def prepare_item(item) -> Dict[str, any]:
            """request-matching payload from the loaded Title"""
            payload = {key: getattr(item, key) for key in model.__fields__.keys()}
            if "languages" in payload:
                payload["languages"] = [lang.code for lang in payload["languages"]]
            if "tags" in payload:
                payload["tags"] = [tag_.name for tag_ in payload["tags"]]
            if "metadata" in payload:
                if with_metadata[-1] == "all" or with_metadata[-1] == "true":
                    md_filter = all
                elif with_metadata[0] == "all-text":
                    md_filter = text_only_filter
                else:
                    md_filter = passed_metadata_filter
                payload["metadata"] = {
                    md.name: md.value
                    if md.kind == KIND_TEXT
                    else base64.standard_b64encode(md.bin_value)
                    for md in filter(md_filter, payload["metadata"])
                }
            return payload

        model = TitlesListSendSchemasHolder.get_for(
            with_languages=with_languages,
            with_tags=with_tags,
            with_metadata=with_metadata,
        )
        for index, item in enumerate(page.items):
            page.items[index] = model(**prepare_item(item))

        return page

    return dress_page(paginate(await qs.all(), params))


@database.transaction()
@router.get(
    "/{ident}",
    tags=["titles"],
    response_model=TitleSendSchema,
    responses={
        404: {"model": Message, "description": "Requested Title not found"},
        200: {"model": TitleSendSchema, "description": "The requested Title"},
    },
)
async def get_title(ident: str):
    try:
        title = await Title.objects.select_all().get(ident=ident)
    except NoMatch:
        return JSONResponse(
            status_code=404, content={"message": f"Title with ID “{ident}” not found"}
        )

    return {
        "ident": title.ident,
        "languages": [lang.code for lang in title.languages],
        "tags": [tag.name for tag in title.tags],
        "metadata": {
            item.name: (
                base64.standard_b64encode(item.bin_value)
                if item.kind == KIND_ILLUSTRATION
                else item.value
            )
            for item in await title.metadata.all()
        },
        "books": [
            {"id": book.id, "name": await book.book_name()} for book in title.books
        ],
    }
