from collections.abc import Callable
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

import cms_backend.mill.process_app_build_requests as mill_process
from cms_backend.db.event import (
    APP_BUILD_REQUESTED_TOPIC,
    create_app_build_requested_event,
)
from cms_backend.db.models import (
    AppBuildPhase,
    Application,
    ApplicationBuild,
    Event,
)
from cms_backend.mill.process_app_build_requests import (
    process_app_build_requests,
)
from cms_backend.utils.datetime import getnow
from cms_backend.utils.github import AppBuildPullRequestResult, github_client


def test_process_app_build_requests_event_missing_keys(
    dbsession: OrmSession,
) -> None:
    event = Event(
        created_at=getnow(),
        topic=APP_BUILD_REQUESTED_TOPIC,
        payload={"unexpected": "value"},
    )
    dbsession.add(event)
    dbsession.flush()
    event_id = event.id

    process_app_build_requests(dbsession)

    assert (
        dbsession.scalars(select(Event).where(Event.id == event_id)).one_or_none()
        is None
    )


def test_process_app_build_requests_unknown_build(
    dbsession: OrmSession,
) -> None:
    event = create_app_build_requested_event(dbsession, build_id=uuid4())
    event_id = event.id

    process_app_build_requests(dbsession)

    assert (
        dbsession.scalars(select(Event).where(Event.id == event_id)).one_or_none()
        is None
    )


def test_process_app_build_requests_starts_build(
    dbsession: OrmSession,
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = create_app_build(
        application=application,
        status="pending",
        phase=AppBuildPhase.REQUESTED.value,
    )
    event = create_app_build_requested_event(dbsession, build_id=build.id)
    event_id = event.id
    build_id = build.id

    result = AppBuildPullRequestResult(
        branch="cms/app-build-test",
        base_sha="basesha",
        pr_number=12,
        pr_url="https://github.test/pr/12",
    )

    with patch.object(
        github_client,
        "create_app_build_pull_request",
        return_value=result,
    ) as mock_create_pull_request:
        process_app_build_requests(dbsession)

    mock_create_pull_request.assert_called_once_with(
        store="android",
        app_name=application.name,
        content_version="2026-05",
        zim_filename="phet_mul_all_maxi_2026-05.zim",
        branch="cms/app-build-test",
        build_id=str(build_id),
    )
    assert (
        dbsession.scalars(select(Event).where(Event.id == event_id)).one_or_none()
        is None
    )
    assert build.phase == AppBuildPhase.CHECKS.value
    assert build.status == "running"
    assert build.pr_number == 12
    assert build.pr_url == "https://github.test/pr/12"


def test_process_app_build_requests_fails_build_on_error(
    dbsession: OrmSession,
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = create_app_build(application=application)
    event = create_app_build_requested_event(dbsession, build_id=build.id)
    event_id = event.id

    with (
        patch.object(
            mill_process,
            "start_app_build",
            side_effect=ValueError("Unexpected error while starting build"),
        ) as mock_start_app_build,
        patch.object(
            mill_process,
            "fail_app_build",
            wraps=mill_process.fail_app_build,
        ) as mock_fail_app_build,
    ):
        process_app_build_requests(dbsession)

    mock_start_app_build.assert_called_once_with(build)
    mock_fail_app_build.assert_called_once_with(
        build,
        "Unexpected error while starting build",
    )
    assert (
        dbsession.scalars(select(Event).where(Event.id == event_id)).one_or_none()
        is None
    )
    assert build.status == "failure"
    assert build.phase is None
    assert build.error == "Unexpected error while starting build"
