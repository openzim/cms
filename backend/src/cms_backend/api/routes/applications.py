from collections.abc import Sequence
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import (
    get_accessible_collection_ids,
    get_accessible_title_ids,
    get_current_account,
    require_permission,
)
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import application as db_application
from cms_backend.db import gen_dbsession
from cms_backend.db.models import Account
from cms_backend.schemas import BaseModel
from cms_backend.schemas.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.schemas.models import ApplicationCreateSchema, ApplicationUpdateSchema
from cms_backend.schemas.orms import ApplicationHistorySchema, ApplicationSchema

router = APIRouter(prefix="/applications", tags=["applications"])


class ApplicationsGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 50
    store: NotEmptyString | None = None
    name: NotEmptyString | None = None


class RevertApplicationSchema(BaseModel):
    comment: NotEmptyString | None = None


@router.get(
    "",
    dependencies=[Depends(require_permission(namespace="application", name="read"))],
)
def get_applications(
    params: Annotated[ApplicationsGetSchema, Query()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ListResponse[ApplicationSchema]:
    results = db_application.get_applications(
        session,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
        store=params.store,
        name=params.name,
        skip=params.skip,
        limit=params.limit,
    )
    return ListResponse[ApplicationSchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )


@router.get(
    "/{name}/{store}",
    dependencies=[Depends(require_permission(namespace="application", name="read"))],
)
def get_application(
    name: Annotated[NotEmptyString, Path()],
    store: Annotated[NotEmptyString, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ApplicationSchema:
    application = db_application.get_application(
        session,
        name=name,
        store=store,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    return db_application.create_application_schema(application)


@router.post(
    "",
    dependencies=[Depends(require_permission(namespace="application", name="create"))],
    status_code=HTTPStatus.CREATED,
)
def create_application(
    request: ApplicationCreateSchema,
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    current_account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ApplicationSchema:
    application = db_application.create_application(
        session,
        payload=request,
        author_id=current_account.id,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    return db_application.create_application_schema(application)


@router.patch(
    "/{name}/{store}",
    dependencies=[Depends(require_permission(namespace="application", name="update"))],
)
def update_application(
    name: Annotated[NotEmptyString, Path()],
    store: Annotated[NotEmptyString, Path()],
    request: ApplicationUpdateSchema,
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    current_account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ApplicationSchema:
    application = db_application.update_application(
        session,
        name=name,
        store=store,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
        author_id=current_account.id,
        payload=request,
    )
    return db_application.create_application_schema(application)


@router.delete(
    "/{name}/{store}",
    status_code=HTTPStatus.NO_CONTENT,
    dependencies=[Depends(require_permission(namespace="application", name="delete"))],
)
def delete_application(
    name: Annotated[NotEmptyString, Path()],
    store: Annotated[NotEmptyString, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> None:
    db_application.delete_application(
        session,
        name=name,
        store=store,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )


@router.get(
    "/{name}/{store}/history",
    dependencies=[Depends(require_permission(namespace="application", name="update"))],
)
def get_application_history(
    name: Annotated[NotEmptyString, Path()],
    store: Annotated[NotEmptyString, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    skip: Annotated[SkipField, Query()] = 0,
    limit: Annotated[LimitFieldMax200, Query()] = 200,
) -> ListResponse[ApplicationHistorySchema]:
    results = db_application.get_application_history(
        session,
        name=name,
        store=store,
        skip=skip,
        limit=limit,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    return ListResponse[ApplicationHistorySchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=skip,
            limit=limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )


@router.get(
    "/{name}/{store}/history/{history_id}",
    dependencies=[Depends(require_permission(namespace="application", name="update"))],
)
def get_application_history_entry(
    name: Annotated[NotEmptyString, Path()],
    store: Annotated[NotEmptyString, Path()],
    history_id: Annotated[UUID, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ApplicationHistorySchema:
    application = db_application.get_application(
        session,
        name=name,
        store=store,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    entry = db_application.get_application_history_entry(
        session,
        name=name,
        store=store,
        history_id=history_id,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    return db_application.create_application_history_schema(
        entry, title_name=application.title_flavour.title.name
    )


@router.patch(
    "/{name}/{store}/revert/{history_id}",
    dependencies=[Depends(require_permission(namespace="application", name="update"))],
)
def revert_application(
    name: Annotated[NotEmptyString, Path()],
    store: Annotated[NotEmptyString, Path()],
    history_id: Annotated[UUID, Path()],
    request: RevertApplicationSchema,
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    accessible_title_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_title_ids)
    ],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    current_account: Annotated[Account, Depends(get_current_account)],
) -> ApplicationSchema:
    """Revert an application to a previous history entry."""
    application = db_application.revert_application(
        session,
        name=name,
        store=store,
        history_id=history_id,
        author_id=current_account.id,
        comment=request.comment,
        accessible_collection_ids=accessible_collection_ids,
        accessible_title_ids=accessible_title_ids,
    )
    return db_application.create_application_schema(application)
