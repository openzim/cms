from collections.abc import Sequence
from datetime import date, timedelta
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import (
    get_accessible_collection_ids,
    get_accessible_title_ids,
    require_permission,
)
from cms_backend.api.routes.http_errors import BadRequestError
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import download_stats, gen_dbsession
from cms_backend.db import title as db_title
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.schemas.fields import NotEmptyString
from cms_backend.schemas.orms import DailyDownloadSchema, TitleFlavourDownloadsSchema
from cms_backend.utils.datetime import getnow

router = APIRouter(prefix="/stats", tags=["stats"])

DEFAULT_RANGE_DAYS = 30


@router.get("/titles/{title_identifier}/downloads")
def get_title_flavour_downloads(
    title_identifier: Annotated[NotEmptyString, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: Annotated[date | None, Query()] = None,
) -> ListResponse[TitleFlavourDownloadsSchema]:
    """Get the daily downloads of every flavour of a title."""
    end = to if to is not None else getnow().date()
    start = from_ if from_ is not None else end - timedelta(days=DEFAULT_RANGE_DAYS)
    if start > end:
        raise BadRequestError("`from` must be before `to`")

    title = db_title.get_title(
        session,
        title_identifier,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )

    items: list[TitleFlavourDownloadsSchema] = []
    for title_flavour in sorted(title.flavours, key=lambda tf: tf.flavour):
        downloads = download_stats.get_downloads_for_flavour(
            session,
            title_id=title.id,
            flavour=title_flavour.flavour,
            start=start,
            end=end,
        )
        items.append(
            TitleFlavourDownloadsSchema(
                flavour=title_flavour.flavour,
                recipe_id=title_flavour.recipe_id,
                downloads=[
                    DailyDownloadSchema(date=day, downloads=count)
                    for day, count in sorted(downloads.items())
                ],
            )
        )

    return ListResponse[TitleFlavourDownloadsSchema](
        meta=calculate_pagination_metadata(
            nb_records=len(items),
            skip=0,
            limit=len(items),
            page_size=len(items),
        ),
        items=items,
    )


@router.get(
    "/downloaded-days",
    dependencies=[Depends(require_permission(namespace="stats", name="read"))],
)
def get_downloaded_days(
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> ListResponse[date]:
    """List the days whose download statistics have been fetched to completion."""
    today = getnow().date()
    range_end = end if end is not None else today
    range_start = start if start is not None else date(today.year - 1, 1, 1)
    if range_start > range_end:
        raise BadRequestError("`start` must be before `end`")

    items = sorted(
        download_stats.get_fetched_days(session, start=range_start, end=range_end)
    )
    return ListResponse[date](
        meta=calculate_pagination_metadata(
            nb_records=len(items),
            skip=0,
            limit=len(items),
            page_size=len(items),
        ),
        items=items,
    )


@router.delete(
    "/downloaded-days/{day}",
    dependencies=[Depends(require_permission(namespace="stats", name="delete"))],
)
def delete_downloaded_day(
    day: Annotated[date, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> Response:
    """Forget that a day was fetched, forcing a refetch of its statistics."""
    if not download_stats.unmark_day_fetched(session, day=day):
        raise RecordDoesNotExistError(
            f"Download statistics for {day} have not been fetched"
        )
    return Response(status_code=HTTPStatus.NO_CONTENT)
