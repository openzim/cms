from collections.abc import Sequence
from http import HTTPStatus
from typing import Annotated, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import (
    get_accessible_collection_ids,
    get_accessible_title_ids,
    get_current_account,
    require_permission,
)
from cms_backend.api.routes.http_errors import (
    BadRequestError,
    ForbiddenError,
    ServerError,
)
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.context import Context
from cms_backend.db import application as db_application
from cms_backend.db import book as db_book
from cms_backend.db import event as db_event
from cms_backend.db import flavour as db_flavour
from cms_backend.db import gen_dbsession
from cms_backend.db import publication as db_publication
from cms_backend.db import publication_permission as db_publication_permission
from cms_backend.db import title as db_title
from cms_backend.db.exceptions import RecordAlreadyExistsError
from cms_backend.db.models import Account, Book
from cms_backend.schemas import BaseModel
from cms_backend.schemas.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.schemas.models import (
    ApplicationPublicationCreateSchema,
    ApplicationPublicationRequestSchema,
    ApplicationStore,
)
from cms_backend.schemas.orms import (
    ApplicationPublicationSchema,
    PublicationCheckSchema,
)
from cms_backend.utils.filename import get_period_and_suffix_from_filename
from cms_backend.utils.github import get_repository_config

router = APIRouter(prefix="/publications", tags=["publications"])


class PublicationsGetSchema(BaseModel):
    name: NotEmptyString
    store: ApplicationStore
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20


class PublicationCheckGetSchema(BaseModel):
    name: NotEmptyString
    store: ApplicationStore


def _resolve_latest_book(session: OrmSession, *, title_id: UUID, flavour: str) -> Book:
    book = db_book.get_latest_prod_book(session, title_id=title_id, flavour=flavour)
    if book is None or not book.filename:
        raise BadRequestError(
            "Unable to determine the content version: no book filename found "
            "for this flavour"
        )
    return book


def _resolve_content_version(filename: str) -> str:
    """Derive the content version from the latest book's filename."""
    try:
        period, suffix = get_period_and_suffix_from_filename(filename)
    except ValueError as exc:
        raise BadRequestError(
            f"Unable to determine the content version from '{filename}'"
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
    if request.store not in Context.publication_stores:
        raise BadRequestError(f"Publication store '{request.store}' is not enabled")

    title = db_title.get_title(
        session,
        request.title_identifier,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    if not db_publication_permission.can_publish(session, current_account, title.id):
        raise ForbiddenError(
            "You do not have permission to publish applications for this title"
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
    book = _resolve_latest_book(
        session,
        title_id=title.id,
        flavour=title_flavour.flavour,
    )
    content_version = _resolve_content_version(book.filename or "")

    try:
        repository_config = get_repository_config(request.store)
    except ValueError as exc:
        raise ServerError(str(exc)) from exc

    if (
        db_publication.get_active_publication_or_none(
            session,
            title_id=title.id,
            flavour=title_flavour.flavour,
            store=request.store,
        )
        is not None
    ):
        raise RecordAlreadyExistsError(
            f"A publication for this {request.store} app is already in progress"
        )

    publication = db_publication.create_publication(
        session,
        payload=ApplicationPublicationCreateSchema(
            title_id=title.id,
            flavour=title_flavour.flavour,
            store=request.store,
            content_version=content_version,
            app_name=app_name,
            repository=repository_config.repo,
            workflow=repository_config.workflow,
            branch=f"cms/publication-{uuid4().hex[:12]}",
            zim_filename=cast(str, book.filename),
            requested_by_id=current_account.id,
        ),
    )
    db_event.create_publication_requested_event(session, publication_id=publication.id)
    return db_publication.create_publication_schema(publication)


@router.get(
    "/check",
    dependencies=[Depends(require_permission(namespace="publication", name="read"))],
)
def check_publication(
    params: Annotated[PublicationCheckGetSchema, Query()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> PublicationCheckSchema:
    """Check whether the current content was already published successfully."""
    application = db_application.get_application(
        session,
        name=params.name,
        store=params.store,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    book = _resolve_latest_book(
        session, title_id=application.title_id, flavour=application.flavour
    )
    content_version = _resolve_content_version(cast(str, book.filename))
    publication = db_publication.get_successful_publication_for_content(
        session,
        title_id=application.title_id,
        flavour=application.flavour,
        store=application.store,
        app_name=application.name,
        content_version=content_version,
    )
    return PublicationCheckSchema(
        content_version=content_version,
        published=publication is not None,
        publication=(
            db_publication.create_publication_schema(publication)
            if publication is not None
            else None
        ),
    )


@router.get(
    "/{publication_id}",
    dependencies=[Depends(require_permission(namespace="publication", name="read"))],
)
def get_publication(
    publication_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ApplicationPublicationSchema:
    publication = db_publication.get_publication(session, publication_id=publication_id)
    return db_publication.create_publication_schema(publication)


@router.post(
    "/{publication_id}/cancel",
    dependencies=[Depends(require_permission(namespace="publication", name="create"))],
)
def cancel_publication(
    publication_id: Annotated[UUID, Path()],
    current_account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ApplicationPublicationSchema:
    """Cancel an in-progress publication and unblock its app."""
    publication = db_publication.get_publication(session, publication_id=publication_id)
    if not db_publication_permission.can_publish(
        session, current_account, publication.title_id
    ):
        raise ForbiddenError(
            "You do not have permission to publish applications for this title"
        )
    if publication.status not in db_publication.ACTIVE_STATUSES:
        raise BadRequestError(f"Publication is already {publication.status}")
    db_publication.cancel_publication(
        session, publication, cancelled_by=current_account
    )
    return db_publication.create_publication_schema(publication)
