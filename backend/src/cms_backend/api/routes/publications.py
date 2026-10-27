from collections.abc import Sequence
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.context import Context as ApiContext
from cms_backend.api.routes.dependencies import (
    get_accessible_collection_ids,
    get_accessible_title_ids,
    get_current_account,
    require_permission,
)
from cms_backend.api.routes.http_errors import (
    BadRequestError,
    ServerError,
)
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import application as db_application
from cms_backend.db import book as db_book
from cms_backend.db import flavour as db_flavour
from cms_backend.db import gen_dbsession
from cms_backend.db import publication as db_publication
from cms_backend.db import title as db_title
from cms_backend.db.models import Account
from cms_backend.schemas import BaseModel
from cms_backend.schemas.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.schemas.models import (
    ApplicationPublicationCreateSchema,
    ApplicationPublicationRequestSchema,
    ApplicationStore,
)
from cms_backend.schemas.orms import ApplicationPublicationSchema
from cms_backend.utils.filename import get_period_and_suffix_from_filename
from cms_backend.utils.github import github_client

router = APIRouter(prefix="/publications", tags=["publications"])


class PublicationsGetSchema(BaseModel):
    name: NotEmptyString
    store: ApplicationStore
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    refresh: bool = False


def _resolve_content_version(
    session: OrmSession, *, title_id: UUID, flavour: str
) -> str:
    """Derive the content version from the latest book's filename."""

    book = db_book.get_latest_prod_book(session, title_id=title_id, flavour=flavour)
    if book is None or not book.filename:
        raise BadRequestError(
            "Unable to determine the content version: no book filename found "
            "for this flavour"
        )

    try:
        period, suffix = get_period_and_suffix_from_filename(book.filename)
    except ValueError as exc:
        raise BadRequestError(
            f"Unable to determine the content version from '{book.filename}'"
        ) from exc
    return f"{period}{suffix}"


@router.get(
    "",
    dependencies=[Depends(require_permission(namespace="publication", name="read"))],
)
def get_publications(
    params: Annotated[PublicationsGetSchema, Query()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ListResponse[ApplicationPublicationSchema]:
    application = db_application.get_application(
        session,
        name=params.name,
        store=params.store,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )

    results = db_publication.get_publications(
        session,
        title_id=application.title_id,
        flavour=application.flavour,
        store=application.store,
        skip=params.skip,
        limit=params.limit,
        refresh=params.refresh,
    )
    return ListResponse[ApplicationPublicationSchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )


@router.post(
    "",
    status_code=HTTPStatus.CREATED,
    dependencies=[Depends(require_permission(namespace="publication", name="create"))],
)
def create_publication(
    request: ApplicationPublicationRequestSchema,
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    current_account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ApplicationPublicationSchema:
    """Trigger an app publication for one title flavour."""
    if request.store not in ApiContext.publication_stores:
        raise BadRequestError(f"Publication store '{request.store}' is not enabled")

    title = db_title.get_title(
        session,
        request.title_identifier,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    title_flavour = db_flavour.get_title_flavour(
        session,
        title.id,
        request.flavour,
        accessible_collection_ids=accessible_collection_ids,
    )
    setting = next(
        (
            application
            for application in title_flavour.applications
            if application.store == request.store
        ),
        None,
    )
    if setting is None or not setting.enabled:
        raise BadRequestError(f"{request.store} publication is not enabled")

    app_name = setting.name
    content_version = _resolve_content_version(
        session,
        title_id=title.id,
        flavour=title_flavour.flavour,
    )

    try:
        result = github_client.publish(
            store=request.store,
            app_name=app_name,
            content_version=content_version,
        )
    except ValueError as exc:
        raise ServerError(str(exc)) from exc

    publication = db_publication.create_publication(
        session,
        payload=ApplicationPublicationCreateSchema(
            title_id=title.id,
            flavour=title_flavour.flavour,
            store=request.store,
            content_version=content_version,
            tag=result.tag,
            commit_sha=result.commit_sha,
            repository=result.repository,
            workflow=result.workflow,
            release_id=result.release_id,
            release_url=result.release_url,
            requested_by_id=current_account.id,
        ),
    )
    return db_publication.create_publication_schema(publication)


@router.get(
    "/{publication_id}",
    dependencies=[Depends(require_permission(namespace="publication", name="read"))],
)
def get_publication(
    publication_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ApplicationPublicationSchema:
    publication = db_publication.get_publication(session, publication_id=publication_id)
    publication = db_publication.refresh_publication(session, publication)
    return db_publication.create_publication_schema(publication)
