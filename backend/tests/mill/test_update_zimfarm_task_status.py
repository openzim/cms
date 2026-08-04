from collections.abc import Callable
from unittest.mock import patch

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import RequestedTask
from cms_backend.mill.update_zimfarm_task_status import update_zimfarm_task_status
from cms_backend.schemas.models import TaskInfo, TaskInfoFlag


def test_update_zimfarm_task_status_success(
    dbsession: OrmSession,
    create_requested_task: Callable[..., RequestedTask],
):
    """Tasks are updated when Zimfarm fetch succeeds"""
    task1 = create_requested_task(status="requested")
    task2 = create_requested_task(status="scraper_running")

    mock_task_info = TaskInfo(
        id="dummy",
        has_email=False,
        partial_zim=False,
        status="succeeded",
        flags=[
            TaskInfoFlag(
                name="download_from", value="s3+https://upload/collections/dummy.zim"
            )
        ],
        progress=100,
        rank=None,
        offliner_definition_version="1.0",
    )

    with patch(
        "cms_backend.mill.update_zimfarm_task_status.fetch_task_from_zimfarm",
        return_value=mock_task_info,
    ) as mock_fetch:
        update_zimfarm_task_status(dbsession)

        assert mock_fetch.call_count == 2

    dbsession.refresh(task1)
    dbsession.refresh(task2)
    assert task1.status == "succeeded"
    assert task2.status == "succeeded"


def test_update_zimfarm_task_status_fetch_error(
    dbsession: OrmSession,
    create_requested_task: Callable[..., RequestedTask],
):
    """When Zimfarm fetch fails, the task keeps its original status"""
    task = create_requested_task(status="requested")

    with patch(
        "cms_backend.mill.update_zimfarm_task_status.fetch_task_from_zimfarm",
        side_effect=Exception("Zimfarm unavailable"),
    ) as mock_fetch:
        update_zimfarm_task_status(dbsession)

        mock_fetch.assert_called_once()

    dbsession.refresh(task)
    assert task.status == "requested"
