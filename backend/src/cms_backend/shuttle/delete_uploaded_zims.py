from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.requested_task import get_requested_tasks
from cms_backend.utils.s3 import get_kiwix_storage_client


def delete_uploaded_zims(session: OrmSession):
    """Delete uploaded zims for requested tasks"""

    logger.info("Deleting zimcheck results from S3")
    nb_deleted, nb_failed = 0, 0
    omit_task_ids: list[UUID] = []

    while True:
        results = get_requested_tasks(
            session,
            status=["failed", "canceled", "succeeded"],
            omit_task_ids=omit_task_ids,
        )
        if not results.nb_records:
            logger.info("No more requested tasks meet criteria to be deleted.")
            break

        for requested_task in results.records:
            omit_task_ids.append(requested_task.id)

            try:
                s3 = get_kiwix_storage_client(requested_task.s3_url)
                s3.delete_object(requested_task.s3_key)
            except Exception:
                logger.exception(
                    "error while deleting zim upload for requested_task "
                    f"{requested_task.id}"
                )
                nb_failed += 1
            else:
                nb_deleted += 1

    logger.info(f"Done deleting zimcheck files from S3: {nb_deleted=}, {nb_failed=}")
