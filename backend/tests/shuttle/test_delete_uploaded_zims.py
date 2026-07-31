from collections.abc import Callable
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import RequestedTask
from cms_backend.shuttle.delete_uploaded_zims import delete_uploaded_zims


def test_delete_uploaded_zims_none(
    dbsession: OrmSession,
):
    with patch(
        "cms_backend.shuttle.delete_uploaded_zims.get_kiwix_storage_client"
    ) as mock_get_s3:
        delete_uploaded_zims(dbsession)
        mock_get_s3.assert_not_called()


def test_delete_uploaded_zims_success(
    dbsession: OrmSession,
    create_requested_task: Callable[..., RequestedTask],
):
    create_requested_task(
        s3_url="s3://bucket/key1.zim",
        s3_key="path/to/key1.zim",
        status="succeeded",
    )
    create_requested_task(
        s3_url="s3://bucket/key2.zim",
        s3_key="path/to/key2.zim",
        status="canceled",
    )

    with patch(
        "cms_backend.shuttle.delete_uploaded_zims.get_kiwix_storage_client"
    ) as mock_get_s3:
        mock_s3 = MagicMock()
        mock_get_s3.return_value = mock_s3

        delete_uploaded_zims(dbsession)

        assert mock_get_s3.call_count == 2
        assert mock_s3.delete_object.call_count == 2
        mock_s3.delete_object.assert_any_call("path/to/key1.zim")
        mock_s3.delete_object.assert_any_call("path/to/key2.zim")


def test_delete_uploaded_zims_s3_error(
    dbsession: OrmSession,
    create_requested_task: Callable[..., RequestedTask],
):
    create_requested_task(
        s3_url="s3://bucket/key.zim",
        s3_key="path/to/key.zim",
        status="failed",
    )

    with patch(
        "cms_backend.shuttle.delete_uploaded_zims.get_kiwix_storage_client"
    ) as mock_get_s3:
        mock_s3 = MagicMock()
        mock_s3.delete_object.side_effect = Exception("S3 error")
        mock_get_s3.return_value = mock_s3

        delete_uploaded_zims(dbsession)

        mock_get_s3.assert_called_once()
        mock_s3.delete_object.assert_called_once_with("path/to/key.zim")
