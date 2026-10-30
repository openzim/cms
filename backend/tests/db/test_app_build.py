from collections.abc import Callable
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import app_build as db_app_build
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import (
    Account,
    AppBuildPhase,
    Application,
    ApplicationBuild,
    Title,
)
from cms_backend.schemas.models import ApplicationBuildCreateSchema
from cms_backend.utils.github import (
    AppBuildPullRequestResult,
    AppBuildResult,
    ChecksSummary,
    github_client,
)


def test_create_app_build(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_application: Callable[..., Application],
    account: Account,
) -> None:
    title = create_title(flavours=["maxi"])
    application = create_application(
        title=title, flavour="maxi", store="android", name="phet"
    )

    build = db_app_build.create_app_build(
        dbsession,
        payload=ApplicationBuildCreateSchema(
            application_id=application.id,
            store="android",
            content_version="2026-05",
            app_name="phet",
            repository="kiwix/kiwix-android-branded",
            workflow="cd.yml",
            branch="cms/app-build-test",
            zim_filename="phet_mul_all_maxi_2026-05.zim",
            requested_by_id=account.id,
        ),
    )

    assert build.status == "pending"
    assert build.phase == AppBuildPhase.REQUESTED.value
    assert build.tag is None
    assert "Build requested" in build.events[0]
    assert build.requested_by_id == account.id
    assert build.application_id == application.id


def test_get_build(
    dbsession: OrmSession,
    build: ApplicationBuild,
) -> None:
    result = db_app_build.get_build(dbsession, build_id=build.id)

    assert result.id == build.id
    assert result.application_id == build.application_id
    assert result.store == build.store


def test_get_build_not_found(
    dbsession: OrmSession,
) -> None:
    with pytest.raises(RecordDoesNotExistError):
        db_app_build.get_build(dbsession, build_id=uuid4())


@pytest.mark.parametrize(
    ("title_name", "flavour", "store", "expected_count"),
    [
        pytest.param(None, None, None, 3, id="no-filters"),
        pytest.param("phet_mul_all", "maxi", None, 1, id="application"),
        pytest.param("phet_mul_all", "mini", None, 1, id="other-flavour"),
        pytest.param(None, None, "android", 2, id="store"),
        pytest.param(
            "wikipedia_en_all", "maxi", "apple", 1, id="application-and-store"
        ),
        pytest.param("wikipedia_en_all", "maxi", "android", 0, id="no-match"),
    ],
)
def test_get_app_builds_filters(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_application: Callable[..., Application],
    create_app_build: Callable[..., ApplicationBuild],
    title_name: str | None,
    flavour: str | None,
    store: str | None,
    expected_count: int,
) -> None:
    phet_title = create_title(name="phet_mul_all", flavours=["maxi", "mini"])
    wikipedia_title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    phet_maxi = create_application(
        title=phet_title, flavour="maxi", store="android", name="phet"
    )
    phet_mini = create_application(
        title=phet_title, flavour="mini", store="android", name="phet2"
    )
    wikipedia_apple = create_application(
        title=wikipedia_title, flavour="maxi", store="apple", name="wikipedia"
    )
    create_app_build(application=phet_maxi, build=0)
    create_app_build(application=phet_mini, build=1)
    create_app_build(application=wikipedia_apple)

    application_id = None
    if title_name is not None:
        title_id = {
            "phet_mul_all": phet_title.id,
            "wikipedia_en_all": wikipedia_title.id,
        }[title_name]
        application = dbsession.scalars(
            select(Application).where(
                Application.title_id == title_id,
                Application.flavour == flavour,
                Application.store == (store or "android"),
            )
        ).one_or_none()
        application_id = application.id if application is not None else uuid4()

    result = db_app_build.get_app_builds(
        dbsession,
        application_id=application_id,
        store=store,
    )

    assert result.nb_records == expected_count
    assert len(result.records) == expected_count


def test_process_app_build_success(
    build: ApplicationBuild,
) -> None:
    build.phase = AppBuildPhase.BUILDING.value
    build.merge_commit_sha = "mergedsha"
    build.tag = "phet_2026.05.0"

    run = {
        "id": 7,
        "html_url": "https://github.test/run/7",
        "status": "completed",
        "conclusion": "success",
    }

    with patch.object(
        github_client, "get_run_for_build", return_value=run
    ) as mock_get_run:
        processed = db_app_build.process_app_build(build)

        assert processed
        assert build.phase == AppBuildPhase.UPLOADED.value
        assert build.run_id == 7
        assert build.run_url == "https://github.test/run/7"

        assert db_app_build.process_app_build(build)
        assert build.status == "success"
        assert build.phase is None

    mock_get_run.assert_called_once_with(
        repo=build.repository,
        workflow=build.workflow,
        tag="phet_2026.05.0",
        commit_sha="mergedsha",
    )


def test_process_app_build_failure(
    build: ApplicationBuild,
) -> None:
    build.phase = AppBuildPhase.BUILDING.value
    build.merge_commit_sha = "mergedsha"
    build.tag = "phet_2026.05.0"

    run = {
        "id": 8,
        "html_url": "https://github.test/run/8",
        "status": "completed",
        "conclusion": "failure",
    }

    with patch.object(
        github_client, "get_run_for_build", return_value=run
    ) as mock_get_run:
        processed = db_app_build.process_app_build(build)

    assert processed
    assert build.status == "failure"
    assert build.error == "Build failed: failure"
    mock_get_run.assert_called_once_with(
        repo=build.repository,
        workflow=build.workflow,
        tag="phet_2026.05.0",
        commit_sha="mergedsha",
    )


def test_get_successful_app_build_for_content(
    dbsession: OrmSession,
    build: ApplicationBuild,
) -> None:
    build.status = "success"
    build.tag = "phet_2026.05.0"

    found = db_app_build.get_successful_app_build_for_content(
        dbsession,
        application_id=build.application_id,
        app_name="phet",
        content_version="2026-05",
    )

    assert found is not None
    assert found.id == build.id

    assert (
        db_app_build.get_successful_app_build_for_content(
            dbsession,
            application_id=build.application_id,
            app_name="phet",
            content_version="2026-06",
        )
        is None
    )


def test_cancel_app_build(
    dbsession: OrmSession,
    build: ApplicationBuild,
    account: Account,
) -> None:
    build.status = "running"
    build.phase = AppBuildPhase.CHECKS.value

    db_app_build.cancel_app_build(dbsession, build, cancelled_by=account)

    assert build.status == "cancelled"
    assert build.phase is None
    assert build.cancelled_by_id == account.id
    assert f"cancelled by {account.display_name}" in build.events[-1]


def test_get_active_build(
    dbsession: OrmSession,
    build: ApplicationBuild,
) -> None:
    active = db_app_build.get_active_app_build_or_none(
        dbsession,
        application_id=build.application_id,
    )
    assert active is not None
    assert active.id == build.id

    build.status = "success"
    dbsession.flush()
    assert (
        db_app_build.get_active_app_build_or_none(
            dbsession,
            application_id=build.application_id,
        )
        is None
    )


def _checks_build(
    create_app_build: Callable[..., ApplicationBuild],
    application: Application,
    **kwargs: Any,
) -> ApplicationBuild:
    params: dict[str, Any] = {
        "status": "running",
        "phase": AppBuildPhase.CHECKS.value,
        "pr_number": 1,
        "pr_url": "https://github.test/pr/1",
    }
    params.update(kwargs)
    return create_app_build(application=application, **params)


def test_process_checks_without_pull_request(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _checks_build(create_app_build, application, pr_number=None, pr_url=None)

    assert db_app_build.process_app_build(build)

    assert build.status == "failure"
    assert build.error == "Build has no pull request"


def test_process_checks_pull_request_not_ready(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _checks_build(create_app_build, application)

    with patch.object(
        github_client, "get_pull_request", return_value=None
    ) as mock_get_pull_request:
        assert db_app_build.process_app_build(build)

    mock_get_pull_request.assert_called_once_with(repo=build.repository, number=1)
    assert build.phase == AppBuildPhase.CHECKS.value
    assert build.status == "running"
    assert build.error is None


def test_process_checks_merged(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _checks_build(create_app_build, application)
    pull = {"merged": True, "merge_commit_sha": "mergedsha"}

    with patch.object(
        github_client, "get_pull_request", return_value=pull
    ) as mock_get_pull_request:
        assert db_app_build.process_app_build(build)

    mock_get_pull_request.assert_called_once_with(repo=build.repository, number=1)
    assert build.phase == AppBuildPhase.RELEASE.value
    assert build.merge_commit_sha == "mergedsha"
    assert "Pull request merged" in build.events[-1]
    assert "https://github.test/pr/1" in build.events[-1]


def test_process_checks_missing_head_sha(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _checks_build(create_app_build, application)
    pull: dict[str, Any] = {"merged": False, "head": {}}

    with patch.object(
        github_client, "get_pull_request", return_value=pull
    ) as mock_get_pull_request:
        assert db_app_build.process_app_build(build)

    mock_get_pull_request.assert_called_once_with(repo=build.repository, number=1)
    assert build.status == "failure"
    assert build.error == "Unable to determine pull request head commit"


def test_process_checks_failed(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _checks_build(create_app_build, application)
    pull = {"merged": False, "head": {"sha": "headsha"}}
    checks = ChecksSummary(total=2, failed=["lint", "unit"])

    with (
        patch.object(
            github_client, "get_pull_request", return_value=pull
        ) as mock_get_pull_request,
        patch.object(
            github_client, "get_checks", return_value=checks
        ) as mock_get_checks,
    ):
        assert db_app_build.process_app_build(build)

    mock_get_pull_request.assert_called_once_with(repo=build.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=build.repository, ref="headsha")
    assert build.status == "failure"
    assert build.error == "Pull request checks failed: lint, unit"


def test_process_checks_pending(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _checks_build(create_app_build, application)
    pull = {"merged": False, "head": {"sha": "headsha"}}
    checks = ChecksSummary(total=2, pending=1)

    with (
        patch.object(
            github_client, "get_pull_request", return_value=pull
        ) as mock_get_pull_request,
        patch.object(
            github_client, "get_checks", return_value=checks
        ) as mock_get_checks,
    ):
        assert db_app_build.process_app_build(build)

    mock_get_pull_request.assert_called_once_with(repo=build.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=build.repository, ref="headsha")
    assert build.phase == AppBuildPhase.CHECKS.value
    assert build.status == "running"


@pytest.mark.parametrize(
    "pull_request",
    [
        pytest.param(
            {"merged": False, "head": {"sha": "headsha"}, "mergeable": False},
            id="not-mergeable",
        ),
        pytest.param(
            {
                "merged": False,
                "head": {"sha": "headsha"},
                "mergeable_state": "dirty",
            },
            id="dirty",
        ),
    ],
)
def test_process_checks_cannot_merge(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
    pull_request: dict[str, Any],
) -> None:
    build = _checks_build(create_app_build, application)
    checks = ChecksSummary(total=1, passed=1)

    with (
        patch.object(
            github_client, "get_pull_request", return_value=pull_request
        ) as mock_get_pull_request,
        patch.object(
            github_client, "get_checks", return_value=checks
        ) as mock_get_checks,
    ):
        assert db_app_build.process_app_build(build)

    mock_get_pull_request.assert_called_once_with(repo=build.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=build.repository, ref="headsha")
    assert build.status == "failure"
    assert build.error == "Pull request cannot be merged"


def test_process_checks_passed(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _checks_build(create_app_build, application)
    pull = {"merged": False, "head": {"sha": "headsha"}}
    checks = ChecksSummary(total=2, passed=2)

    with (
        patch.object(
            github_client, "get_pull_request", return_value=pull
        ) as mock_get_pull_request,
        patch.object(
            github_client, "get_checks", return_value=checks
        ) as mock_get_checks,
    ):
        assert db_app_build.process_app_build(build)

    mock_get_pull_request.assert_called_once_with(repo=build.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=build.repository, ref="headsha")
    assert build.phase == AppBuildPhase.MERGE.value
    assert build.status == "running"
    assert build.events[-1].endswith(
        "Pull request checks passed - https://github.test/pr/1/checks"
    )


def _merge_build(
    create_app_build: Callable[..., ApplicationBuild],
    application: Application,
    **kwargs: Any,
) -> ApplicationBuild:
    params: dict[str, Any] = {
        "status": "running",
        "phase": AppBuildPhase.MERGE.value,
        "pr_number": 1,
        "pr_url": "https://github.test/pr/1",
    }
    params.update(kwargs)
    return create_app_build(application=application, **params)


def test_process_merge_without_pull_request(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _merge_build(create_app_build, application, pr_number=None, pr_url=None)

    assert db_app_build.process_app_build(build)

    assert build.status == "failure"
    assert build.error == "Build has no pull request"


def test_process_merge_pull_request_not_ready(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _merge_build(create_app_build, application)

    with patch.object(
        github_client, "get_pull_request", return_value=None
    ) as mock_get_pull_request:
        assert db_app_build.process_app_build(build)

    mock_get_pull_request.assert_called_once_with(repo=build.repository, number=1)
    assert build.phase == AppBuildPhase.MERGE.value
    assert build.status == "running"


def test_process_merge_already_merged(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _merge_build(create_app_build, application)
    pull = {"merged": True, "merge_commit_sha": "mergedsha"}

    with patch.object(
        github_client, "get_pull_request", return_value=pull
    ) as mock_get_pull_request:
        assert db_app_build.process_app_build(build)

    mock_get_pull_request.assert_called_once_with(repo=build.repository, number=1)
    assert build.phase == AppBuildPhase.RELEASE.value
    assert build.merge_commit_sha == "mergedsha"


def test_process_merge_missing_head_sha(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _merge_build(create_app_build, application)
    pull = {"merged": False, "head": {"sha": ""}}

    with patch.object(
        github_client, "get_pull_request", return_value=pull
    ) as mock_get_pull_request:
        assert db_app_build.process_app_build(build)

    mock_get_pull_request.assert_called_once_with(repo=build.repository, number=1)
    assert build.status == "failure"
    assert build.error == "Unable to determine pull request head commit"


def test_process_merge_checks_failed(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _merge_build(create_app_build, application)
    pull = {"merged": False, "head": {"sha": "headsha"}}
    checks = ChecksSummary(total=1, failed=["lint"])

    with (
        patch.object(
            github_client, "get_pull_request", return_value=pull
        ) as mock_get_pull_request,
        patch.object(
            github_client, "get_checks", return_value=checks
        ) as mock_get_checks,
    ):
        assert db_app_build.process_app_build(build)

    mock_get_pull_request.assert_called_once_with(repo=build.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=build.repository, ref="headsha")
    assert build.status == "failure"
    assert build.error == "Pull request checks failed: lint"


def test_process_merge_checks_pending(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _merge_build(create_app_build, application)
    pull = {"merged": False, "head": {"sha": "headsha"}}
    checks = ChecksSummary(total=2, pending=1)

    with (
        patch.object(
            github_client, "get_pull_request", return_value=pull
        ) as mock_get_pull_request,
        patch.object(
            github_client, "get_checks", return_value=checks
        ) as mock_get_checks,
    ):
        assert db_app_build.process_app_build(build)

    mock_get_pull_request.assert_called_once_with(repo=build.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=build.repository, ref="headsha")
    assert build.phase == AppBuildPhase.MERGE.value
    assert build.status == "running"


@pytest.mark.parametrize(
    "pull_request",
    [
        pytest.param(
            {"merged": False, "head": {"sha": "headsha"}, "mergeable": False},
            id="not-mergeable",
        ),
        pytest.param(
            {
                "merged": False,
                "head": {"sha": "headsha"},
                "mergeable_state": "blocked",
            },
            id="blocked",
        ),
        pytest.param(
            {
                "merged": False,
                "head": {"sha": "headsha"},
                "mergeable_state": "dirty",
            },
            id="dirty",
        ),
    ],
)
def test_process_merge_cannot_merge(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
    pull_request: dict[str, Any],
) -> None:
    build = _merge_build(create_app_build, application)
    checks = ChecksSummary(total=1, passed=1)

    with (
        patch.object(
            github_client, "get_pull_request", return_value=pull_request
        ) as mock_get_pull_request,
        patch.object(
            github_client, "get_checks", return_value=checks
        ) as mock_get_checks,
    ):
        assert db_app_build.process_app_build(build)

    mock_get_pull_request.assert_called_once_with(repo=build.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=build.repository, ref="headsha")
    assert build.status == "failure"
    assert build.error == "Pull request cannot be merged"


def test_process_merge_refused(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _merge_build(create_app_build, application)
    pull = {"merged": False, "head": {"sha": "headsha"}}
    checks = ChecksSummary(total=1, passed=1)

    with (
        patch.object(
            github_client, "get_pull_request", return_value=pull
        ) as mock_get_pull_request,
        patch.object(
            github_client, "get_checks", return_value=checks
        ) as mock_get_checks,
        patch.object(
            github_client, "merge_pull_request", return_value=False
        ) as mock_merge_pull_request,
    ):
        assert db_app_build.process_app_build(build)

    mock_get_pull_request.assert_called_once_with(repo=build.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=build.repository, ref="headsha")
    mock_merge_pull_request.assert_called_once_with(
        repo=build.repository, number=1, sha="headsha"
    )
    assert build.phase == AppBuildPhase.MERGE.value
    assert build.status == "running"
    assert build.merge_commit_sha is None


def test_process_merge_confirmed(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _merge_build(create_app_build, application)
    pulls = [
        {"merged": False, "head": {"sha": "headsha"}},
        {"merged": True, "merge_commit_sha": "mergedsha"},
    ]
    checks = ChecksSummary(total=1, passed=1)

    with (
        patch.object(
            github_client, "get_pull_request", side_effect=pulls
        ) as mock_get_pull_request,
        patch.object(
            github_client, "get_checks", return_value=checks
        ) as mock_get_checks,
        patch.object(
            github_client, "merge_pull_request", return_value=True
        ) as mock_merge_pull_request,
    ):
        assert db_app_build.process_app_build(build)

    assert mock_get_pull_request.call_count == 2
    mock_get_checks.assert_called_once_with(repo=build.repository, ref="headsha")
    mock_merge_pull_request.assert_called_once_with(
        repo=build.repository, number=1, sha="headsha"
    )
    assert build.phase == AppBuildPhase.RELEASE.value
    assert build.merge_commit_sha == "mergedsha"
    assert "Pull request merged" in build.events[-1]


def test_process_release_without_merge_commit(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = create_app_build(
        application=application,
        status="running",
        phase=AppBuildPhase.RELEASE.value,
        merge_commit_sha=None,
    )

    assert db_app_build.process_app_build(build)

    assert build.status == "failure"
    assert build.error == "Build has no merged commit"


def test_process_release_value_error(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = create_app_build(
        application=application,
        status="running",
        phase=AppBuildPhase.RELEASE.value,
        merge_commit_sha="mergedsha",
    )
    error = ValueError("Unable to find a free tag for 'phet_2026.05'")

    with patch.object(
        github_client, "create_release_on_sha", side_effect=error
    ) as mock_create_release_on_sha:
        assert db_app_build.process_app_build(build)

    mock_create_release_on_sha.assert_called_once_with(
        repo=build.repository,
        app_name=build.app_name,
        content_version=build.content_version,
        sha="mergedsha",
        workflow=build.workflow,
    )
    assert build.status == "failure"
    assert build.error == "Unable to find a free tag for 'phet_2026.05'"


def test_process_release_success(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = create_app_build(
        application=application,
        status="running",
        phase=AppBuildPhase.RELEASE.value,
        merge_commit_sha="mergedsha",
    )
    result = AppBuildResult(
        tag="phet_2026.05.0",
        commit_sha="mergedsha",
        release_id=9,
        release_url="https://github.test/release/9",
        repository=build.repository,
        workflow=build.workflow,
    )

    with patch.object(
        github_client, "create_release_on_sha", return_value=result
    ) as mock_create_release_on_sha:
        assert db_app_build.process_app_build(build)

    mock_create_release_on_sha.assert_called_once_with(
        repo=build.repository,
        app_name=build.app_name,
        content_version=build.content_version,
        sha="mergedsha",
        workflow=build.workflow,
    )
    assert build.tag == "phet_2026.05.0"
    assert build.release_id == 9
    assert build.release_url == "https://github.test/release/9"
    assert build.phase == AppBuildPhase.BUILDING.value
    assert build.events[-1].endswith(
        "Release phet_2026.05.0 created - https://github.test/release/9"
    )


def _building_build(
    create_app_build: Callable[..., ApplicationBuild],
    application: Application,
    **kwargs: Any,
) -> ApplicationBuild:
    params: dict[str, Any] = {
        "status": "running",
        "phase": AppBuildPhase.BUILDING.value,
        "tag": "phet_2026.05.0",
        "merge_commit_sha": "mergedsha",
        "run_id": 55,
        "run_url": "https://github.test/run/55",
    }
    params.update(kwargs)
    return create_app_build(application=application, **params)


@pytest.mark.parametrize(
    ("run", "expected_status", "expected_phase", "expected_error"),
    [
        pytest.param(
            {
                "id": 55,
                "html_url": "https://github.test/run/55",
                "status": "completed",
                "conclusion": "success",
            },
            "running",
            AppBuildPhase.UPLOADED.value,
            None,
            id="success",
        ),
        pytest.param(
            {
                "id": 55,
                "html_url": "https://github.test/run/55",
                "status": "completed",
                "conclusion": "cancelled",
            },
            "cancelled",
            None,
            None,
            id="cancelled",
        ),
        pytest.param(
            {
                "id": 55,
                "html_url": "https://github.test/run/55",
                "status": "completed",
                "conclusion": "failure",
            },
            "failure",
            None,
            "Build failed: failure",
            id="failure",
        ),
        pytest.param(
            {
                "id": 55,
                "html_url": "https://github.test/run/55",
                "status": "completed",
                "conclusion": None,
            },
            "failure",
            None,
            "Build failed: workflow failed",
            id="unknown-conclusion",
        ),
        pytest.param(
            {
                "id": 55,
                "html_url": "https://github.test/run/55",
                "status": "in_progress",
            },
            "running",
            AppBuildPhase.BUILDING.value,
            None,
            id="in-progress",
        ),
    ],
)
def test_process_building_run_states(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
    run: dict[str, Any],
    expected_status: str,
    expected_phase: str | None,
    expected_error: str | None,
) -> None:
    build = _building_build(create_app_build, application)

    with (
        patch.object(
            github_client, "get_workflow_run", return_value=run
        ) as mock_get_workflow_run,
        patch.object(github_client, "get_run_for_build") as mock_get_run_for_build,
    ):
        assert db_app_build.process_app_build(build)

    mock_get_workflow_run.assert_called_once_with(repo=build.repository, run_id=55)
    mock_get_run_for_build.assert_not_called()
    assert build.status == expected_status
    assert build.phase == expected_phase
    assert build.error == expected_error


def test_process_building_waits_for_run(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = _building_build(create_app_build, application, run_id=None, run_url=None)

    with patch.object(
        github_client, "get_run_for_build", return_value=None
    ) as mock_get_run_for_build:
        assert db_app_build.process_app_build(build)

    mock_get_run_for_build.assert_called_once_with(
        repo=build.repository,
        workflow=build.workflow,
        tag="phet_2026.05.0",
        commit_sha="mergedsha",
    )
    assert build.phase == AppBuildPhase.BUILDING.value
    assert build.status == "running"
    assert build.run_id is None


def test_process_app_build_uploaded_phase(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = create_app_build(
        application=application,
        status="running",
        phase=AppBuildPhase.UPLOADED.value,
    )

    assert db_app_build.process_app_build(build)

    assert build.status == "success"
    assert build.phase is None
    assert build.phase_started_at is None
    assert build.events[-1].endswith("Uploaded to android; awaiting store review")


def test_process_app_build_requested(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = create_app_build(
        application=application,
        status="pending",
        phase=AppBuildPhase.REQUESTED.value,
    )

    with patch.object(db_app_build, "_process_requested") as mock_process_requested:
        assert db_app_build.process_app_build(build)

    mock_process_requested.assert_called_once_with(build)


def test_process_requested_value_error(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = create_app_build(
        application=application,
        status="pending",
        phase=AppBuildPhase.REQUESTED.value,
    )
    error = ValueError(
        "Unable to find 'phet/info.json' in 'kiwix/kiwix-android-branded'"
    )

    with patch.object(
        github_client, "create_app_build_pull_request", side_effect=error
    ) as mock_create_pull_request:
        assert db_app_build.process_app_build(build)

    mock_create_pull_request.assert_called_once_with(
        store="android",
        app_name=build.app_name,
        content_version="2026-05",
        zim_filename="phet_mul_all_maxi_2026-05.zim",
        branch="cms/app-build-test",
        build_id=str(build.id),
    )
    assert build.status == "failure"
    assert (
        build.error
        == "Unable to find 'phet/info.json' in 'kiwix/kiwix-android-branded'"
    )


def test_process_requested_without_changes(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = create_app_build(
        application=application,
        status="pending",
        phase=AppBuildPhase.REQUESTED.value,
    )
    pull_request_result = AppBuildPullRequestResult(
        branch="main", base_sha="basesha", pr_number=None, pr_url=None
    )

    with patch.object(
        github_client,
        "create_app_build_pull_request",
        return_value=pull_request_result,
    ) as mock_create_pull_request:
        assert db_app_build.process_app_build(build)

    mock_create_pull_request.assert_called_once_with(
        store="android",
        app_name=build.app_name,
        content_version="2026-05",
        zim_filename="phet_mul_all_maxi_2026-05.zim",
        branch="cms/app-build-test",
        build_id=str(build.id),
    )
    assert build.branch == "main"
    assert build.commit_sha == "basesha"
    assert build.merge_commit_sha == "basesha"
    assert build.pr_number is None
    assert build.phase == AppBuildPhase.RELEASE.value
    assert "Configuration already up to date" in build.events[-1]


def test_process_requested_opens_pull_request(
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = create_app_build(
        application=application,
        status="pending",
        phase=AppBuildPhase.REQUESTED.value,
    )
    pull_request_result = AppBuildPullRequestResult(
        branch="cms/app-build-test",
        base_sha="basesha",
        pr_number=12,
        pr_url="https://github.test/pr/12",
    )

    with patch.object(
        github_client,
        "create_app_build_pull_request",
        return_value=pull_request_result,
    ) as mock_create_pull_request:
        assert db_app_build.process_app_build(build)

    mock_create_pull_request.assert_called_once_with(
        store="android",
        app_name=build.app_name,
        content_version="2026-05",
        zim_filename="phet_mul_all_maxi_2026-05.zim",
        branch="cms/app-build-test",
        build_id=str(build.id),
    )
    assert build.branch == "cms/app-build-test"
    assert build.commit_sha == "basesha"
    assert build.pr_number == 12
    assert build.pr_url == "https://github.test/pr/12"
    assert build.phase == AppBuildPhase.CHECKS.value
    assert build.status == "running"
    assert "Configuration changes prepared" in build.events[-2]
    assert "Pull request opened" in build.events[-1]
