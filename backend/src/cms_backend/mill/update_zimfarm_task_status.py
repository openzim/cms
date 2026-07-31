from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.models import Book, RequestedTask
from cms_backend.db.requested_task import get_requested_tasks, update_task_status
from cms_backend.schemas.orms import RequestedTaskLightSchema
from cms_backend.utils.requests import fetch_task_from_zimfarm


def update_books_task_id(session: OrmSession, requested_task: RequestedTaskLightSchema):
    books = session.scalars(
        select(Book).where(
            Book.task_id.is_(None), Book.recipe_id == requested_task.recipe_id
        )
    ).all()
    for book in books:
        book.task_id = requested_task.id
        session.add(book)


def update_zimfarm_task_status(session: OrmSession):
    logger.info("Updating status of requested tasks from zimfarm")
    nb_tasks_updated, nb_failed = 0, 0
    omit_task_ids = list(
        session.scalars(
            select(RequestedTask.id).where(
                RequestedTask.status.in_(["failed", "canceled", "succeeded"])
            )
        ).all()
    )
    while True:
        results = get_requested_tasks(session, omit_task_ids=omit_task_ids)
        if not results.records:
            logger.info("No more requested tasks meet criteria to be updated")
            break

        for requested_task in results.records:
            omit_task_ids.append(requested_task.id)
            try:
                zimfarm_task = fetch_task_from_zimfarm(requested_task.id)
                update_task_status(session, requested_task.id, zimfarm_task.status)
            except Exception:
                logger.exception(f"error while updating {requested_task.id} status")
                nb_failed += 1
            else:
                # update book zimfarm task if none has been updated
                update_books_task_id(session, requested_task)
                session.commit()
                nb_tasks_updated += 1

    logger.info(
        f"Done updating status of tasks from zimfarm: {nb_tasks_updated=}, {nb_failed=}"
    )
