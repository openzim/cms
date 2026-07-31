from collections.abc import Sequence
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import CollectionTitle, TitleUpload
from cms_backend.schemas.models import TaskInfo, TaskInfoFlag, ZimfarmTask
from cms_backend.schemas.orms import ListResult, TitleUploadLightSchema


def create_title_upload(
    session: OrmSession,
    *,
    task_id: UUID,
    s3_key: str,
    recipe_id: UUID,
    title_id: UUID,
    requested_by: UUID,
) -> TitleUpload:
    """Create a title upload in DB"""
    upload = TitleUpload(
        id=task_id,
        recipe_id=recipe_id,
        title_id=title_id,
        s3_key=s3_key,
        requested_by_id=requested_by,
        status="requested",
    )
    session.add(upload)
    session.flush()
    return upload


def get_title_upload_or_none(
    session: OrmSession,
    task_id: UUID,
    *,
    accessible_collection_ids: Sequence[UUID] | None = None,
) -> TitleUpload | None:
    """Get a title uploadif one exists, otherwise None"""
    return session.scalars(
        select(TitleUpload)
        .where(
            TitleUpload.id == task_id,
            exists().where(
                CollectionTitle.title_id == TitleUpload.title_id,
                CollectionTitle.collection_id.in_(accessible_collection_ids or []),
            )
            | (accessible_collection_ids is None),
        )
        .options(
            selectinload(TitleUpload.title),
            selectinload(TitleUpload.requested_by),
        )
    ).one_or_none()


def get_last_title_upload_for_recipe(
    session: OrmSession, recipe_id: UUID
) -> TitleUpload | None:
    """Get the most recent title upload for a recipe if one exists"""
    return session.scalars(
        select(TitleUpload)
        .where(TitleUpload.recipe_id == recipe_id)
        .order_by(TitleUpload.created_at.desc())
    ).first()


def get_title_upload(
    session: OrmSession,
    title_upload_id: UUID,
    *,
    accessible_collection_ids: Sequence[UUID] | None = None,
) -> TitleUpload:
    """Get a title upload if one exists, otherwise raise RecordDoesNotExistError"""
    if title_upload := get_title_upload_or_none(
        session, title_upload_id, accessible_collection_ids=accessible_collection_ids
    ):
        return title_upload
    raise RecordDoesNotExistError(
        f"Title upload with ID {title_upload_id} does not exist"
    )


def update_title_upload_status(
    session: OrmSession,
    task_id: UUID,
    status: str,
    *,
    accessible_collection_ids: Sequence[UUID] | None = None,
    s3_file_deleted: bool | None = None,
) -> TitleUpload:
    upload = get_title_upload(
        session, task_id, accessible_collection_ids=accessible_collection_ids
    )
    upload.status = status
    if s3_file_deleted is not None:
        upload.s3_file_deleted = s3_file_deleted
    session.add(upload)
    session.flush()
    return upload


def create_title_upload_schema(
    title_upload: TitleUpload,
) -> TitleUploadLightSchema:
    return TitleUploadLightSchema(
        id=title_upload.id,
        created_at=title_upload.created_at,
        status=title_upload.status,
        recipe_id=title_upload.recipe_id,
        requested_by=title_upload.requested_by.username
        if title_upload.requested_by
        else None,
        s3_key=title_upload.s3_key,
        title_id=title_upload.title_id,
        updated_at=title_upload.updated_at,
    )


def get_title_uploads(
    session: OrmSession,
    *,
    skip: int = 0,
    limit: int = 20,
    omit_task_ids: list[UUID] | None = None,
    status: list[str] | None = None,
    title_id: UUID | None = None,
    recipe_id: UUID | None = None,
    accessible_collection_ids: Sequence[UUID] | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
    exclude_status: list[str] | None = None,
    s3_file_deleted: bool | None = None,
) -> ListResult[TitleUploadLightSchema]:
    stmt = (
        select(TitleUpload)
        .where(
            TitleUpload.status.in_(status or []) | (status is None),
            TitleUpload.id.not_in(omit_task_ids or []) | (omit_task_ids is None),
            (TitleUpload.title_id == title_id) | (title_id is None),
            (TitleUpload.recipe_id == recipe_id) | (recipe_id is None),
            exists().where(
                CollectionTitle.title_id == TitleUpload.title_id,
                CollectionTitle.collection_id.in_(accessible_collection_ids or []),
            )
            | (accessible_collection_ids is None),
            TitleUpload.status.not_in(exclude_status or []) | (exclude_status is None),
            (TitleUpload.s3_file_deleted == bool(s3_file_deleted))
            | (s3_file_deleted is None),
        )
        .options(selectinload(TitleUpload.requested_by))
    )
    if sort_order == "asc":
        order_clauses = [TitleUpload.created_at]
    else:
        order_clauses = [TitleUpload.created_at.desc()]
    return ListResult[TitleUploadLightSchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            create_title_upload_schema(title_upload)
            for title_upload in session.scalars(
                stmt.offset(skip).limit(limit).order_by(*order_clauses)
            ).all()
        ],
    )


def create_zimfarm_task_info(task: dict[str, Any]) -> TaskInfo:
    """Transforms a task object(dict) returned by Zimfarm API

    The final object is ready to be consumed by the frontend, with most checks for
    consistency and complex computation already done.
    """

    # parse object (dict) as pydantic object
    zimfarm_task = ZimfarmTask.model_validate(task)

    # transform into object ready to be returned by the BFF
    return TaskInfo(
        id=zimfarm_task.id,
        has_email=bool(
            zimfarm_task.notification
            and zimfarm_task.notification.ended
            and zimfarm_task.notification.ended.webhook
        ),
        partial_zim=bool(
            zimfarm_task.container
            and zimfarm_task.container.progress
            and zimfarm_task.container.progress.partial_zim
        ),
        status=zimfarm_task.status,
        flags=(
            sorted(
                [
                    TaskInfoFlag(name=key, value=value)
                    for (key, value) in zimfarm_task.config.offliner.items()
                    if key != "offliner_id"
                ],
                key=lambda flag: flag.name,
            )
        ),
        progress=(
            int(zimfarm_task.container.progress.overall)
            if (
                zimfarm_task.container
                and zimfarm_task.container.progress
                and zimfarm_task.container.progress.overall
            )
            else 0
        ),
        rank=zimfarm_task.rank,
        offliner_definition_version=zimfarm_task.version,
    )
