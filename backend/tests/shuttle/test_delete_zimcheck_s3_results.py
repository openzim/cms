from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest
from kiwixstorage import AuthenticationError  # pyright: ignore[reportMissingTypeStubs]
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book
from cms_backend.shuttle.delete_zimcheck_s3_results import delete_zimcheck_s3_results


def test_delete_zimcheck_s3_results_authentication_error(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    monkeypatch: pytest.MonkeyPatch,
):
    book1 = create_book(
        location_kind="staging",
        zimcheck_result_url="https://www.example.com/zimcheck1.json",
    )
    book1.zimcheck_summary = {
        "zimcheck_version": "1.0.0",
        "status": False,
        "checks": ["internal_urls"],
        "error_count": 1,
        "warning_count": 1,
        "retcode": 1,
    }
    dbsession.add(book1)
    monkeypatch.setattr(
        "cms_backend.shuttle.context.Context.zimcheck_results_s3_bucket_uri",
        "s3+http://minio:9000/?keyId=minio_key&secretAccessKey=minio_secret&bucketName=zimfarm-zimchecks",
    )
    with patch(
        "cms_backend.shuttle.delete_zimcheck_s3_results.KiwixStorage"
    ) as mock_kiwix_storage_cls:
        mock_s3 = MagicMock()
        mock_kiwix_storage_cls.return_value = mock_s3
        mock_s3.check_credentials.return_value = False
        with pytest.raises(AuthenticationError, match="check_credentials failed"):
            delete_zimcheck_s3_results(dbsession)


def test_delete_zimcheck_s3_results_processes_eligible_books(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    monkeypatch: pytest.MonkeyPatch,
):
    book1 = create_book(
        location_kind="prod",
        zimcheck_result_url="https://www.example.com/zimcheck1.json",
    )
    book1.zimcheck_summary = {
        "zimcheck_version": "1.0.0",
        "status": False,
        "checks": ["internal_urls"],
        "error_count": 1,
        "warning_count": 1,
        "retcode": 1,
    }
    dbsession.add(book1)
    # should skip book because it is in quarantine
    book2 = create_book(
        location_kind="quarantine",
        zimcheck_result_url="https://www.example.com/zimcheck2.json",
    )
    # should skip book3 because it's in staging
    book3 = create_book(
        location_kind="staging",
        zimcheck_result_url="https://www.example.com/zimcheck3.json",
    )

    monkeypatch.setattr(
        "cms_backend.shuttle.context.Context.zimcheck_results_s3_bucket_uri",
        "s3+http://minio:9000/?keyId=minio_key&secretAccessKey=minio_secret&bucketName=zimfarm-zimchecks",
    )
    with patch(
        "cms_backend.shuttle.delete_zimcheck_s3_results.get_kiwix_storage_client"
    ) as mock_kiwix_storage:
        mock_s3 = MagicMock()
        mock_kiwix_storage.return_value = mock_s3
        delete_zimcheck_s3_results(dbsession)
        assert mock_s3.delete_object.call_count == 1

    assert book1.zimcheck_s3_deleted is True
    assert book2.zimcheck_s3_deleted is False
    assert book3.zimcheck_s3_deleted is False
