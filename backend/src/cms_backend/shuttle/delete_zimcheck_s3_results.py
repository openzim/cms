from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.models import Book
from cms_backend.shuttle.context import Context as ShuttleContext
from cms_backend.utils.s3 import get_kiwix_storage_client


def delete_zimcheck_s3_results(session: OrmSession):
    """Delete zimcheck results from S3"""
    if not ShuttleContext.zimcheck_results_s3_bucket_uri:
        logger.warning(
            "Cannot delete zimcheck results from S3 because results upload uri is "
            "empty."
        )
        return
    s3 = get_kiwix_storage_client(ShuttleContext.zimcheck_results_s3_bucket_uri)

    logger.info("Deleting zimcheck results from S3")
    nb_deleted, nb_failed = 0, 0

    omit_book_ids: list[UUID] = []
    while True:
        books = session.scalars(
            select(Book)
            .where(
                Book.zimcheck_result_url.is_not(None),
                Book.zimcheck_s3_deleted.is_(False),
                Book.location_kind.in_(["prod", "deleted"]),
                Book.id.not_in(omit_book_ids),
            )
            .limit(50)
            .order_by(Book.created_at)
        ).all()

        if not books:
            logger.info(
                "No more books meet criteria for zimcheck results to be deleted."
            )
            break

        for book in books:
            omit_book_ids.append(book.id)
            try:
                s3.delete_object(
                    book.zimcheck_result_url.split("/")[-1],  # pyright: ignore[reportOptionalMemberAccess]
                )
            except Exception:
                logger.exception(
                    f"error while deleting zimcheck results for book {book.id}"
                )
                nb_failed += 1
            else:
                book.zimcheck_s3_deleted = True
                session.add(book)
                session.commit()
                nb_deleted += 1

    logger.info(f"Done deleting zimcheck files from S3: {nb_deleted=}, {nb_failed=}")
