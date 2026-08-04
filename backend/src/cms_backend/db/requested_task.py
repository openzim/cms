from collections.abc import Sequence
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import RequestedTask
from cms_backend.schemas.models import TaskInfo, TaskInfoFlag, ZimfarmTask
from cms_backend.schemas.orms import ListResult, RequestedTaskLightSchema


def create_requested_task(
    session: OrmSession,
    *,
    task_id: UUID,
    s3_url: str,
    s3_key: str,
    recipe_id: UUID,
    requested_by: UUID,
    collection_id: UUID,
    collection_path: str,
) -> RequestedTask:
    """Create a requested task in DB"""
    requested_task = RequestedTask(
        id=task_id,
        recipe_id=recipe_id,
        s3_url=s3_url,
        s3_key=s3_key,
        requested_by_id=requested_by,
        collection_id=collection_id,
        collection_path=collection_path,
        status="requested",
    )
    session.add(requested_task)
    session.flush()
    return requested_task


def get_requested_task_or_none(
    session: OrmSession,
    task_id: UUID,
    *,
    accessible_collection_ids: Sequence[UUID] | None = None,
) -> RequestedTask | None:
    """Get a requested task if one exists, otherwise None"""
    return session.scalars(
        select(RequestedTask)
        .where(
            RequestedTask.id == task_id,
            RequestedTask.collection_id.in_(accessible_collection_ids or [])
            | (accessible_collection_ids is None),
        )
        .options(
            selectinload(RequestedTask.collection),
            selectinload(RequestedTask.requested_by),
        )
    ).one_or_none()


def get_requested_task(
    session: OrmSession,
    task_id: UUID,
    *,
    accessible_collection_ids: Sequence[UUID] | None = None,
) -> RequestedTask:
    """Get a requested task if one exists, otherwise raise RecordDoesNotExistError"""
    if requested_task := get_requested_task_or_none(
        session, task_id, accessible_collection_ids=accessible_collection_ids
    ):
        return requested_task
    raise RecordDoesNotExistError(f"Requested task with ID {task_id} does not exist")


def update_task_status(
    session: OrmSession,
    task_id: UUID,
    status: str,
    *,
    accessible_collection_ids: Sequence[UUID] | None = None,
) -> RequestedTask:
    task = get_requested_task(
        session, task_id, accessible_collection_ids=accessible_collection_ids
    )
    task.status = status
    session.add(task)
    session.flush()
    return task


def create_requested_task_schema(
    requested_task: RequestedTask,
) -> RequestedTaskLightSchema:
    return RequestedTaskLightSchema(
        id=requested_task.id,
        created_at=requested_task.created_at,
        status=requested_task.status,
        recipe_id=requested_task.recipe_id,
        requested_by=requested_task.requested_by.username
        if requested_task.requested_by
        else None,
        s3_key=requested_task.s3_key,
        s3_url=requested_task.s3_url,
        collection_path=requested_task.collection_path,
        collection_id=requested_task.collection_id,
    )


def get_requested_tasks(
    session: OrmSession,
    *,
    skip: int = 0,
    limit: int = 20,
    omit_task_ids: list[UUID] | None = None,
    status: list[str] | None = None,
    collection_id: UUID | None = None,
    recipe_id: UUID | None = None,
    accessible_collection_ids: Sequence[UUID] | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
) -> ListResult[RequestedTaskLightSchema]:
    stmt = (
        select(RequestedTask)
        .where(
            RequestedTask.collection_id.in_(accessible_collection_ids or [])
            | (accessible_collection_ids is None),
            RequestedTask.status.in_(status or []) | (status is None),
            RequestedTask.id.not_in(omit_task_ids or []) | (omit_task_ids is None),
            (RequestedTask.collection_id == collection_id) | (collection_id is None),
            (RequestedTask.recipe_id == recipe_id) | (recipe_id is None),
        )
        .options(selectinload(RequestedTask.requested_by))
    )
    if sort_order == "asc":
        order_clauses = [RequestedTask.created_at]
    else:
        order_clauses = [RequestedTask.created_at.desc()]
    return ListResult[RequestedTaskLightSchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            create_requested_task_schema(requested_task)
            for requested_task in session.scalars(
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
