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
from cms_backend.db import app_build as db_app_build
from cms_backend.db import app_build_permission as db_app_build_permission
from cms_backend.db import application as db_application
from cms_backend.db import book as db_book
from cms_backend.db import event as db_event
from cms_backend.db import flavour as db_flavour
from cms_backend.db import gen_dbsession
from cms_backend.db import title as db_title
from cms_backend.db.exceptions import RecordAlreadyExistsError
from cms_backend.db.models import Account, Book
from cms_backend.schemas import BaseModel
from cms_backend.schemas.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.schemas.models import (
    ApplicationBuildCreateSchema,
    ApplicationBuildRequestSchema,
    ApplicationStore,
)
from cms_backend.schemas.orms import (
    AppBuildCheckSchema,
    ApplicationBuildSchema,
)
from cms_backend.utils.filename import get_period_and_suffix_from_filename
from cms_backend.utils.github import get_repository_config

router = APIRouter(prefix="/app-builds", tags=["app-builds"])


class AppBuildsGetSchema(BaseModel):
    name: NotEmptyString
    store: ApplicationStore
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20


class AppBuildCheckGetSchema(BaseModel):
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
    dependencies=[Depends(require_permission(namespace="app_build", name="read"))],
)
def get_app_builds(
    params: Annotated[AppBuildsGetSchema, Query()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ListResponse[ApplicationBuildSchema]:
    application = db_application.get_application(
        session,
        name=params.name,
        store=params.store,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )

    results = db_app_build.get_app_builds(
        session,
        application_id=application.id,
        store=application.store,
        skip=params.skip,
        limit=params.limit,
    )
    return ListResponse[ApplicationBuildSchema](
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
    dependencies=[Depends(require_permission(namespace="app_build", name="create"))],
)
def create_app_build(
    request: ApplicationBuildRequestSchema,
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    current_account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ApplicationBuildSchema:
    """Trigger an app build for one title flavour."""
    if request.store not in Context.app_build_stores:
        raise BadRequestError(f"Build store '{request.store}' is not enabled")

    title = db_title.get_title(
        session,
        request.title_identifier,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    if not db_app_build_permission.can_build(session, current_account, title.id):
        raise ForbiddenError(
            "You do not have permission to build applications for this title"
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
        raise BadRequestError(f"{request.store} build is not enabled")

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
        db_app_build.get_active_app_build_or_none(
            session,
            application_id=setting.id,
        )
        is not None
    ):
        raise RecordAlreadyExistsError(
            f"A build for this {request.store} app is already in progress"
        )

    build = db_app_build.create_app_build(
        session,
        payload=ApplicationBuildCreateSchema(
            application_id=setting.id,
            store=request.store,
            content_version=content_version,
            app_name=app_name,
            repository=repository_config.repo,
            workflow=repository_config.workflow,
            branch=f"cms/app-build-{uuid4().hex[:12]}",
            zim_filename=cast(str, book.filename),
            requested_by_id=current_account.id,
        ),
    )
    db_event.create_app_build_requested_event(session, build_id=build.id)
    return db_app_build.create_app_build_schema(build)


@router.get(
    "/check",
    dependencies=[Depends(require_permission(namespace="app_build", name="read"))],
)
def check_app_build(
    params: Annotated[AppBuildCheckGetSchema, Query()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> AppBuildCheckSchema:
    """Check whether the current content was already built successfully."""
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
    build = db_app_build.get_successful_app_build_for_content(
        session,
        application_id=application.id,
        app_name=application.name,
        content_version=content_version,
    )
    return AppBuildCheckSchema(
        content_version=content_version,
        built=build is not None,
        app_build=(
            db_app_build.create_app_build_schema(build) if build is not None else None
        ),
    )


@router.get(
    "/{build_id}",
    dependencies=[Depends(require_permission(namespace="app_build", name="read"))],
)
def get_app_build(
    build_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ApplicationBuildSchema:
    build = db_app_build.get_build(session, build_id=build_id)
    return db_app_build.create_app_build_schema(build)


@router.post(
    "/{build_id}/cancel",
    dependencies=[Depends(require_permission(namespace="app_build", name="create"))],
)
def cancel_app_build(
    build_id: Annotated[UUID, Path()],
    current_account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ApplicationBuildSchema:
    """Cancel an in-progress build and unblock its app."""
    build = db_app_build.get_build(session, build_id=build_id)
    if not db_app_build_permission.can_build(
        session, current_account, build.application.title_id
    ):
        raise ForbiddenError(
            "You do not have permission to build applications for this title"
        )
    if build.status not in db_app_build.ACTIVE_STATUSES:
        raise BadRequestError(f"Build is already {build.status}")
    db_app_build.cancel_app_build(session, build, cancelled_by=current_account)
    return db_app_build.create_app_build_schema(build)
