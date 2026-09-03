from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.context import Context
from cms_backend.db.title_upload import get_title_uploads, update_title_upload_status
from cms_backend.utils.s3 import get_kiwix_storage_client


def delete_uploaded_zims(session: OrmSession):
    """Delete uploaded zims for title uploads"""

    if not Context.zim_upload_s3_bucket_uri:
        logger.warning(
            "Cannot delete files for title uploads from S3 because upload uri is empty."
        )
        return

    logger.info("Deleting zimcheck results from S3")
    nb_deleted, nb_failed = 0, 0
    omit_task_ids: list[UUID] = []

    while True:
        results = get_title_uploads(
            session,
            status=["failed", "canceled", "succeeded"],
            omit_task_ids=omit_task_ids,
            s3_file_deleted=False,
        )
        if not results.nb_records:
            logger.info("No more title uploads meet criteria for files to be deleted.")
            break

        for title_upload in results.records:
            omit_task_ids.append(title_upload.id)

            try:
                s3 = get_kiwix_storage_client(Context.zim_upload_s3_bucket_uri)
                s3.delete_object(title_upload.s3_key)
                update_title_upload_status(
                    session, title_upload.id, title_upload.status, s3_file_deleted=True
                )
            except Exception:
                logger.exception(f"error while deleting zim upload {title_upload.id}")
                nb_failed += 1
            else:
                nb_deleted += 1

    logger.info(
        f"Done deleting title upload files from S3: {nb_deleted=}, {nb_failed=}"
    )
