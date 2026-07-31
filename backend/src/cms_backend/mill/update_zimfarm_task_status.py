from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.models import Book
from cms_backend.db.title_upload import get_title_uploads, update_title_upload_status
from cms_backend.schemas.orms import TitleUploadLightSchema
from cms_backend.utils.requests import fetch_task_from_zimfarm


def update_books_task_id(session: OrmSession, title_upload: TitleUploadLightSchema):
    books = session.scalars(
        select(Book).where(
            Book.task_id.is_(None), Book.recipe_id == title_upload.recipe_id
        )
    ).all()
    for book in books:
        book.task_id = title_upload.id
        session.add(book)


def update_title_uploads_status(session: OrmSession):
    logger.info("Updating status of title uploads from zimfarm")
    nb_tasks_updated, nb_failed = 0, 0
    omit_task_ids: list[UUID] = []
    while True:
        results = get_title_uploads(
            session,
            omit_task_ids=omit_task_ids,
            exclude_status=["failed", "canceled", "succeeded"],
        )
        if not results.records:
            logger.info("No more title uploads meet criteria to be updated")
            break

        for title_upload in results.records:
            omit_task_ids.append(title_upload.id)
            try:
                zimfarm_task = fetch_task_from_zimfarm(title_upload.id)
                update_title_upload_status(
                    session, title_upload.id, zimfarm_task.status
                )
            except Exception:
                logger.exception(f"error while updating {title_upload.id} status")
                nb_failed += 1
            else:
                # update book zimfarm task if none has been updated
                update_books_task_id(session, title_upload)
                session.commit()
                nb_tasks_updated += 1

    logger.info(
        f"Done updating status of tasks from zimfarm: {nb_tasks_updated=}, {nb_failed=}"
    )
