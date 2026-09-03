from collections.abc import Callable
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import (
    Account,
    Collection,
    CollectionTitle,
    Title,
    TitleUpload,
)
from cms_backend.db.title_upload import (
    create_title_upload as db_create_title_upload,
)
from cms_backend.db.title_upload import (
    get_title_upload,
    get_title_upload_or_none,
    get_title_uploads,
    update_title_upload_status,
)


def test_create_title_upload(
    dbsession: OrmSession,
    account: Account,
    title: Title,
):
    """Create a requested task in DB"""
    task_id = uuid4()
    s3_key = "path/to/key.zim"

    task = db_create_title_upload(
        dbsession,
        recipe_id=uuid4(),
        title_id=title.id,
        task_id=task_id,
        s3_key=s3_key,
        requested_by=account.id,
    )

    assert task is not None
    assert task.id == task_id
    assert task.s3_key == s3_key
    assert task.status == "requested"
    assert task.requested_by_id == account.id
    assert task.title_id == title.id


def test_get_title_upload_or_none_returns_none(
    dbsession: OrmSession,
):
    """Returns None if the requested task does not exist"""
    result = get_title_upload_or_none(dbsession, task_id=uuid4())
    assert result is None


def test_get_title_upload_not_found(
    dbsession: OrmSession,
):
    """Raises RecordDoesNotExistError if requested task does not exist"""
    with pytest.raises(RecordDoesNotExistError):
        get_title_upload(dbsession, title_upload_id=uuid4())


def test_get_title_upload_exists(dbsession: OrmSession, title_upload: TitleUpload):
    """Returns the requested task if it exists"""
    result = get_title_upload(dbsession, title_upload_id=title_upload.id)
    assert result is not None
    assert result.id == title_upload.id
    assert result.status == title_upload.status


def test_get_title_upload_not_accessible(
    dbsession: OrmSession,
    create_title_upload: Callable[..., TitleUpload],
):
    """Returns None when task exists but is not in accessible_collection_ids"""
    task = create_title_upload()
    dbsession.flush()

    result = get_title_upload_or_none(
        dbsession, task_id=task.id, accessible_collection_ids=[]
    )
    assert result is None


def test_get_title_upload_accessible(
    dbsession: OrmSession,
    collection: Collection,
    title: Title,
    create_collection_title: Callable[..., CollectionTitle],
    create_title_upload: Callable[..., TitleUpload],
):
    """Returns the task when it is in accessible_collection_ids"""

    create_collection_title(title, collection)
    task = create_title_upload(title_id=title.id)
    dbsession.flush()

    result = get_title_upload_or_none(
        dbsession,
        task_id=task.id,
        accessible_collection_ids=[collection.id],  # pyright: ignore[reportArgumentType]
    )
    assert result is not None
    assert result.id == task.id


def test_get_title_upload_not_accessible_raises(
    dbsession: OrmSession,
    create_title_upload: Callable[..., TitleUpload],
):
    """Raises RecordDoesNotExistError when task is not in accessible_collection_ids"""
    task = create_title_upload()
    dbsession.flush()

    with pytest.raises(RecordDoesNotExistError):
        get_title_upload(
            dbsession, title_upload_id=task.id, accessible_collection_ids=[]
        )


def test_update_title_upload_status(dbsession: OrmSession, title_upload: TitleUpload):
    """Updates the status of a requested task"""
    assert title_upload.status == "requested"

    update_title_upload_status(dbsession, task_id=title_upload.id, status="canceled")

    # Refresh from DB and verify
    dbsession.refresh(title_upload)
    assert title_upload.status == "canceled"


@pytest.mark.parametrize(
    "skip,limit,expected_count",
    [
        pytest.param(0, 3, 3, id="first-page"),
        pytest.param(3, 3, 3, id="second-page"),
        pytest.param(6, 3, 2, id="third-page-partial"),
        pytest.param(8, 3, 0, id="page-num-too-high-no-results"),
        pytest.param(0, 1, 1, id="first-page-with-low-limit"),
        pytest.param(0, 20, 8, id="first-page-with-high-limit"),
    ],
)
def test_get_title_uploads_pagination(
    dbsession: OrmSession,
    create_title_upload: Callable[..., TitleUpload],
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test that get_title_uploads works correctly with skip and limit"""
    # Create 8 tasks
    for _ in range(8):
        create_title_upload()

    dbsession.flush()

    results = get_title_uploads(dbsession, skip=skip, limit=limit)
    assert results.nb_records == 8
    assert len(results.records) <= limit
    assert len(results.records) == expected_count


@pytest.mark.parametrize(
    "status_filter,expected_count",
    [
        pytest.param(None, 8, id="no-filter"),
        pytest.param(["requested"], 3, id="requested-only"),
        pytest.param(["canceled"], 3, id="canceled-only"),
        pytest.param(["completed"], 2, id="completed-only"),
        pytest.param(["requested", "canceled"], 6, id="requested-or-canceled"),
    ],
)
def test_get_title_uploads_filter_by_status(
    dbsession: OrmSession,
    create_title_upload: Callable[..., TitleUpload],
    status_filter: list[str] | None,
    expected_count: int,
):
    """Test that get_title_uploads filters by status correctly"""
    # Create tasks with different statuses
    for _ in range(3):
        create_title_upload(status="requested")
    for _ in range(3):
        create_title_upload(status="canceled")
    for _ in range(2):
        create_title_upload(status="completed")

    dbsession.flush()

    results = get_title_uploads(dbsession, skip=0, limit=20, status=status_filter)
    assert results.nb_records == expected_count
    assert len(results.records) == expected_count
