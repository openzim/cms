from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import TitleUpload
from cms_backend.mill.delete_uploaded_zims import delete_uploaded_zims


def test_delete_uploaded_zims_none(
    dbsession: OrmSession,
):
    with patch(
        "cms_backend.mill.delete_uploaded_zims.get_kiwix_storage_client"
    ) as mock_get_s3:
        delete_uploaded_zims(dbsession)
        mock_get_s3.assert_not_called()


def test_delete_uploaded_zims_success(
    dbsession: OrmSession,
    create_title_upload: Callable[..., TitleUpload],
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "cms_backend.context.Context.zim_upload_s3_bucket_uri",
        "s3+http://minio:9000/?keyId=minio_key&secretAccessKey=minio_secret&bucketName=zimfarm-zimchecks",
    )
    create_title_upload(
        s3_key="path/to/key1.zim",
        status="succeeded",
    )
    create_title_upload(
        s3_key="path/to/key2.zim",
        status="canceled",
    )

    with patch(
        "cms_backend.mill.delete_uploaded_zims.get_kiwix_storage_client"
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
    create_title_upload: Callable[..., TitleUpload],
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "cms_backend.context.Context.zim_upload_s3_bucket_uri",
        "s3+http://minio:9000/?keyId=minio_key&secretAccessKey=minio_secret&bucketName=zimfarm-zimchecks",
    )
    create_title_upload(
        s3_key="path/to/key.zim",
        status="failed",
    )

    with patch(
        "cms_backend.mill.delete_uploaded_zims.get_kiwix_storage_client"
    ) as mock_get_s3:
        mock_s3 = MagicMock()
        mock_s3.delete_object.side_effect = Exception("S3 error")
        mock_get_s3.return_value = mock_s3

        delete_uploaded_zims(dbsession)

        mock_get_s3.assert_called_once()
        mock_s3.delete_object.assert_called_once_with("path/to/key.zim")
