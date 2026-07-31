from collections.abc import Callable
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Account, Collection, RequestedTask
from cms_backend.db.requested_task import (
    create_requested_task as db_create_requested_task,
)
from cms_backend.db.requested_task import (
    get_requested_task,
    get_requested_task_or_none,
    get_requested_tasks,
    update_task_status,
)


def test_create_requested_task(
    dbsession: OrmSession, account: Account, collection: Collection
):
    """Create a requested task in DB"""
    task_id = uuid4()
    s3_url = "s3://bucket/key.zim"
    s3_key = "path/to/key.zim"

    task = db_create_requested_task(
        dbsession,
        recipe_id=uuid4(),
        task_id=task_id,
        s3_url=s3_url,
        s3_key=s3_key,
        requested_by=account.id,
        collection_id=collection.id,
    )

    assert task is not None
    assert task.id == task_id
    assert task.s3_url == s3_url
    assert task.s3_key == s3_key
    assert task.status == "requested"
    assert task.requested_by_id == account.id
    assert task.collection_id == collection.id


def test_get_requested_task_or_none_returns_none(
    dbsession: OrmSession,
):
    """Returns None if the requested task does not exist"""
    result = get_requested_task_or_none(dbsession, task_id=uuid4())
    assert result is None


def test_get_requested_task_not_found(
    dbsession: OrmSession,
):
    """Raises RecordDoesNotExistError if requested task does not exist"""
    with pytest.raises(RecordDoesNotExistError):
        get_requested_task(dbsession, task_id=uuid4())


def test_get_requested_task_exists(
    dbsession: OrmSession, requested_task: RequestedTask
):
    """Returns the requested task if it exists"""
    result = get_requested_task(dbsession, task_id=requested_task.id)
    assert result is not None
    assert result.id == requested_task.id
    assert result.status == requested_task.status


def test_get_requested_task_not_accessible(
    dbsession: OrmSession,
    create_requested_task: Callable[..., RequestedTask],
):
    """Returns None when task exists but is not in accessible_collection_ids"""
    task = create_requested_task()
    dbsession.flush()

    result = get_requested_task_or_none(
        dbsession, task_id=task.id, accessible_collection_ids=[]
    )
    assert result is None


def test_get_requested_task_accessible(
    dbsession: OrmSession,
    create_requested_task: Callable[..., RequestedTask],
):
    """Returns the task when it is in accessible_collection_ids"""
    task = create_requested_task()
    dbsession.flush()

    result = get_requested_task_or_none(
        dbsession,
        task_id=task.id,
        accessible_collection_ids=[task.collection_id],  # pyright: ignore[reportArgumentType]
    )
    assert result is not None
    assert result.id == task.id


def test_get_requested_task_not_accessible_raises(
    dbsession: OrmSession,
    create_requested_task: Callable[..., RequestedTask],
):
    """Raises RecordDoesNotExistError when task is not in accessible_collection_ids"""
    task = create_requested_task()
    dbsession.flush()

    with pytest.raises(RecordDoesNotExistError):
        get_requested_task(dbsession, task_id=task.id, accessible_collection_ids=[])


def test_update_task_status(dbsession: OrmSession, requested_task: RequestedTask):
    """Updates the status of a requested task"""
    assert requested_task.status == "requested"

    update_task_status(dbsession, task_id=requested_task.id, status="canceled")

    # Refresh from DB and verify
    dbsession.refresh(requested_task)
    assert requested_task.status == "canceled"


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
def test_get_requested_tasks_pagination(
    dbsession: OrmSession,
    create_requested_task: Callable[..., RequestedTask],
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test that get_requested_tasks works correctly with skip and limit"""
    # Create 8 tasks
    for _ in range(8):
        create_requested_task()

    dbsession.flush()

    results = get_requested_tasks(dbsession, skip=skip, limit=limit)
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
def test_get_requested_tasks_filter_by_status(
    dbsession: OrmSession,
    create_requested_task: Callable[..., RequestedTask],
    status_filter: list[str] | None,
    expected_count: int,
):
    """Test that get_requested_tasks filters by status correctly"""
    # Create tasks with different statuses
    for _ in range(3):
        create_requested_task(status="requested")
    for _ in range(3):
        create_requested_task(status="canceled")
    for _ in range(2):
        create_requested_task(status="completed")

    dbsession.flush()

    results = get_requested_tasks(dbsession, skip=0, limit=20, status=status_filter)
    assert results.nb_records == expected_count
    assert len(results.records) == expected_count
