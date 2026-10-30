from collections.abc import Callable
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import publication as db_publication
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import (
    Account,
    ApplicationPublication,
    PublicationPhase,
    Title,
)
from cms_backend.schemas.models import ApplicationPublicationCreateSchema
from cms_backend.utils.github import (
    ChecksSummary,
    PublicationPullRequestResult,
    PublicationResult,
    github_client,
)


def test_create_publication(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    account: Account,
) -> None:
    title = create_title(flavours=["maxi"])

    publication = db_publication.create_publication(
        dbsession,
        payload=ApplicationPublicationCreateSchema(
            title_id=title.id,
            flavour="maxi",
            store="android",
            content_version="2026-05",
            app_name="phet",
            repository="kiwix/kiwix-android-branded",
            workflow="cd.yml",
            branch="cms/publication-test",
            zim_filename="phet_mul_all_maxi_2026-05.zim",
            requested_by_id=account.id,
        ),
    )

    assert publication.status == "pending"
    assert publication.phase == PublicationPhase.REQUESTED.value
    assert publication.tag is None
    assert "Publication requested" in publication.events[0]
    assert publication.requested_by_id == account.id


def test_get_publication(
    dbsession: OrmSession,
    publication: ApplicationPublication,
) -> None:
    result = db_publication.get_publication(dbsession, publication_id=publication.id)

    assert result.id == publication.id
    assert result.title_id == publication.title_id
    assert result.flavour == publication.flavour
    assert result.store == publication.store


def test_get_publication_not_found(
    dbsession: OrmSession,
) -> None:
    with pytest.raises(RecordDoesNotExistError):
        db_publication.get_publication(dbsession, publication_id=uuid4())


@pytest.mark.parametrize(
    ("title_name", "flavour", "store", "expected_count"),
    [
        pytest.param(None, None, None, 3, id="no-filters"),
        pytest.param("phet_mul_all", None, None, 2, id="title"),
        pytest.param("wikipedia_en_all", None, None, 1, id="title-single"),
        pytest.param("phet_mul_all", "mini", None, 1, id="title-and-flavour"),
        pytest.param(None, None, "android", 2, id="store"),
        pytest.param(None, "maxi", None, 2, id="flavour"),
        pytest.param("phet_mul_all", "maxi", "android", 1, id="all-filters"),
        pytest.param("wikipedia_en_all", "maxi", "android", 0, id="no-match"),
    ],
)
def test_get_publications_filters(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_publication: Callable[..., ApplicationPublication],
    title_name: str | None,
    flavour: str | None,
    store: str | None,
    expected_count: int,
) -> None:
    phet_title = create_title(name="phet_mul_all", flavours=["maxi", "mini"])
    wikipedia_title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    create_publication(
        title=phet_title, flavour="maxi", store="android", app_name="phet", build=0
    )
    create_publication(
        title=phet_title, flavour="mini", store="android", app_name="phet", build=1
    )
    create_publication(
        title=wikipedia_title,
        flavour="maxi",
        store="apple",
        app_name="wikipedia",
    )

    title_id = {
        "phet_mul_all": phet_title.id,
        "wikipedia_en_all": wikipedia_title.id,
    }.get(title_name or "")

    result = db_publication.get_publications(
        dbsession,
        title_id=title_id,
        flavour=flavour,
        store=store,
    )

    assert result.nb_records == expected_count
    assert len(result.records) == expected_count


def test_advance_publication_success(
    publication: ApplicationPublication,
) -> None:
    publication.phase = PublicationPhase.BUILDING.value
    publication.merge_commit_sha = "mergedsha"
    publication.tag = "phet_2026.05.0"

    run = {
        "id": 7,
        "html_url": "https://github.test/run/7",
        "status": "completed",
        "conclusion": "success",
    }

    with patch.object(
        github_client, "get_run_for_publication", return_value=run
    ) as mock_get_run:
        advanced = db_publication.advance_publication(publication)

        assert advanced
        assert publication.phase == PublicationPhase.STORE.value
        assert publication.run_id == 7
        assert publication.run_url == "https://github.test/run/7"

        assert db_publication.advance_publication(publication)
        assert publication.status == "success"
        assert publication.phase is None

    mock_get_run.assert_called_once_with(
        repo=publication.repository,
        workflow=publication.workflow,
        tag="phet_2026.05.0",
        commit_sha="mergedsha",
    )


def test_advance_publication_failure(
    publication: ApplicationPublication,
) -> None:
    publication.phase = PublicationPhase.BUILDING.value
    publication.merge_commit_sha = "mergedsha"
    publication.tag = "phet_2026.05.0"

    run = {
        "id": 8,
        "html_url": "https://github.test/run/8",
        "status": "completed",
        "conclusion": "failure",
    }

    with patch.object(
        github_client, "get_run_for_publication", return_value=run
    ) as mock_get_run:
        advanced = db_publication.advance_publication(publication)

    assert advanced
    assert publication.status == "failure"
    assert publication.error == "Build failed: failure"
    mock_get_run.assert_called_once_with(
        repo=publication.repository,
        workflow=publication.workflow,
        tag="phet_2026.05.0",
        commit_sha="mergedsha",
    )


def test_get_successful_publication_for_content(
    dbsession: OrmSession,
    publication: ApplicationPublication,
) -> None:
    publication.status = "success"
    publication.tag = "phet_2026.05.0"

    found = db_publication.get_successful_publication_for_content(
        dbsession,
        title_id=publication.title_id,
        flavour=publication.flavour,
        store=publication.store,
        app_name="phet",
        content_version="2026-05",
    )

    assert found is not None
    assert found.id == publication.id

    assert (
        db_publication.get_successful_publication_for_content(
            dbsession,
            title_id=publication.title_id,
            flavour=publication.flavour,
            store=publication.store,
            app_name="phet",
            content_version="2026-06",
        )
        is None
    )


def test_cancel_publication(
    dbsession: OrmSession,
    publication: ApplicationPublication,
    account: Account,
) -> None:
    publication.status = "running"
    publication.phase = PublicationPhase.CHECKS.value

    db_publication.cancel_publication(dbsession, publication, cancelled_by=account)

    assert publication.status == "cancelled"
    assert publication.phase is None
    assert publication.cancelled_by_id == account.id
    assert f"cancelled by {account.display_name}" in publication.events[-1]


def test_get_active_publication(
    dbsession: OrmSession,
    publication: ApplicationPublication,
) -> None:
    active = db_publication.get_active_publication_or_none(
        dbsession,
        title_id=publication.title_id,
        flavour=publication.flavour,
        store=publication.store,
    )
    assert active is not None
    assert active.id == publication.id

    publication.status = "success"
    dbsession.flush()
    assert (
        db_publication.get_active_publication_or_none(
            dbsession,
            title_id=publication.title_id,
            flavour=publication.flavour,
            store=publication.store,
        )
        is None
    )


def _checks_publication(
    create_publication: Callable[..., ApplicationPublication],
    **kwargs: Any,
) -> ApplicationPublication:
    params: dict[str, Any] = {
        "status": "running",
        "phase": PublicationPhase.CHECKS.value,
        "pr_number": 1,
        "pr_url": "https://github.test/pr/1",
    }
    params.update(kwargs)
    return create_publication(**params)


def test_advance_checks_without_pull_request(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _checks_publication(create_publication, pr_number=None, pr_url=None)

    assert db_publication.advance_publication(publication)

    assert publication.status == "failure"
    assert publication.error == "Publication has no pull request"


def test_advance_checks_pull_request_not_ready(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _checks_publication(create_publication)

    with patch.object(
        github_client, "get_pull_request", return_value=None
    ) as mock_get_pull_request:
        assert db_publication.advance_publication(publication)

    mock_get_pull_request.assert_called_once_with(repo=publication.repository, number=1)
    assert publication.phase == PublicationPhase.CHECKS.value
    assert publication.status == "running"
    assert publication.error is None


def test_advance_checks_merged(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _checks_publication(create_publication)
    pull = {"merged": True, "merge_commit_sha": "mergedsha"}

    with patch.object(
        github_client, "get_pull_request", return_value=pull
    ) as mock_get_pull_request:
        assert db_publication.advance_publication(publication)

    mock_get_pull_request.assert_called_once_with(repo=publication.repository, number=1)
    assert publication.phase == PublicationPhase.RELEASE.value
    assert publication.merge_commit_sha == "mergedsha"
    assert "Pull request merged" in publication.events[-1]
    assert "https://github.test/pr/1" in publication.events[-1]


def test_advance_checks_missing_head_sha(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _checks_publication(create_publication)
    pull: dict[str, Any] = {"merged": False, "head": {}}

    with patch.object(
        github_client, "get_pull_request", return_value=pull
    ) as mock_get_pull_request:
        assert db_publication.advance_publication(publication)

    mock_get_pull_request.assert_called_once_with(repo=publication.repository, number=1)
    assert publication.status == "failure"
    assert publication.error == "Unable to determine pull request head commit"


def test_advance_checks_failed(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _checks_publication(create_publication)
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
        assert db_publication.advance_publication(publication)

    mock_get_pull_request.assert_called_once_with(repo=publication.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=publication.repository, ref="headsha")
    assert publication.status == "failure"
    assert publication.error == "Pull request checks failed: lint, unit"


def test_advance_checks_pending(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _checks_publication(create_publication)
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
        assert db_publication.advance_publication(publication)

    mock_get_pull_request.assert_called_once_with(repo=publication.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=publication.repository, ref="headsha")
    assert publication.phase == PublicationPhase.CHECKS.value
    assert publication.status == "running"


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
def test_advance_checks_cannot_merge(
    create_publication: Callable[..., ApplicationPublication],
    pull_request: dict[str, Any],
) -> None:
    publication = _checks_publication(create_publication)
    checks = ChecksSummary(total=1, passed=1)

    with (
        patch.object(
            github_client, "get_pull_request", return_value=pull_request
        ) as mock_get_pull_request,
        patch.object(
            github_client, "get_checks", return_value=checks
        ) as mock_get_checks,
    ):
        assert db_publication.advance_publication(publication)

    mock_get_pull_request.assert_called_once_with(repo=publication.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=publication.repository, ref="headsha")
    assert publication.status == "failure"
    assert publication.error == "Pull request cannot be merged"


def test_advance_checks_passed(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _checks_publication(create_publication)
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
        assert db_publication.advance_publication(publication)

    mock_get_pull_request.assert_called_once_with(repo=publication.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=publication.repository, ref="headsha")
    assert publication.phase == PublicationPhase.MERGE.value
    assert publication.status == "running"
    assert publication.events[-1].endswith(
        "Pull request checks passed - https://github.test/pr/1/checks"
    )


def _merge_publication(
    create_publication: Callable[..., ApplicationPublication],
    **kwargs: Any,
) -> ApplicationPublication:
    params: dict[str, Any] = {
        "status": "running",
        "phase": PublicationPhase.MERGE.value,
        "pr_number": 1,
        "pr_url": "https://github.test/pr/1",
    }
    params.update(kwargs)
    return create_publication(**params)


def test_advance_merge_without_pull_request(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _merge_publication(create_publication, pr_number=None, pr_url=None)

    assert db_publication.advance_publication(publication)

    assert publication.status == "failure"
    assert publication.error == "Publication has no pull request"


def test_advance_merge_pull_request_not_ready(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _merge_publication(create_publication)

    with patch.object(
        github_client, "get_pull_request", return_value=None
    ) as mock_get_pull_request:
        assert db_publication.advance_publication(publication)

    mock_get_pull_request.assert_called_once_with(repo=publication.repository, number=1)
    assert publication.phase == PublicationPhase.MERGE.value
    assert publication.status == "running"


def test_advance_merge_already_merged(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _merge_publication(create_publication)
    pull = {"merged": True, "merge_commit_sha": "mergedsha"}

    with patch.object(
        github_client, "get_pull_request", return_value=pull
    ) as mock_get_pull_request:
        assert db_publication.advance_publication(publication)

    mock_get_pull_request.assert_called_once_with(repo=publication.repository, number=1)
    assert publication.phase == PublicationPhase.RELEASE.value
    assert publication.merge_commit_sha == "mergedsha"


def test_advance_merge_missing_head_sha(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _merge_publication(create_publication)
    pull = {"merged": False, "head": {"sha": ""}}

    with patch.object(
        github_client, "get_pull_request", return_value=pull
    ) as mock_get_pull_request:
        assert db_publication.advance_publication(publication)

    mock_get_pull_request.assert_called_once_with(repo=publication.repository, number=1)
    assert publication.status == "failure"
    assert publication.error == "Unable to determine pull request head commit"


def test_advance_merge_checks_failed(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _merge_publication(create_publication)
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
        assert db_publication.advance_publication(publication)

    mock_get_pull_request.assert_called_once_with(repo=publication.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=publication.repository, ref="headsha")
    assert publication.status == "failure"
    assert publication.error == "Pull request checks failed: lint"


def test_advance_merge_checks_pending(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _merge_publication(create_publication)
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
        assert db_publication.advance_publication(publication)

    mock_get_pull_request.assert_called_once_with(repo=publication.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=publication.repository, ref="headsha")
    assert publication.phase == PublicationPhase.MERGE.value
    assert publication.status == "running"


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
def test_advance_merge_cannot_merge(
    create_publication: Callable[..., ApplicationPublication],
    pull_request: dict[str, Any],
) -> None:
    publication = _merge_publication(create_publication)
    checks = ChecksSummary(total=1, passed=1)

    with (
        patch.object(
            github_client, "get_pull_request", return_value=pull_request
        ) as mock_get_pull_request,
        patch.object(
            github_client, "get_checks", return_value=checks
        ) as mock_get_checks,
    ):
        assert db_publication.advance_publication(publication)

    mock_get_pull_request.assert_called_once_with(repo=publication.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=publication.repository, ref="headsha")
    assert publication.status == "failure"
    assert publication.error == "Pull request cannot be merged"


def test_advance_merge_refused(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _merge_publication(create_publication)
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
        assert db_publication.advance_publication(publication)

    mock_get_pull_request.assert_called_once_with(repo=publication.repository, number=1)
    mock_get_checks.assert_called_once_with(repo=publication.repository, ref="headsha")
    mock_merge_pull_request.assert_called_once_with(
        repo=publication.repository, number=1, sha="headsha"
    )
    assert publication.phase == PublicationPhase.MERGE.value
    assert publication.status == "running"
    assert publication.merge_commit_sha is None


def test_advance_merge_confirmed(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _merge_publication(create_publication)
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
        assert db_publication.advance_publication(publication)

    assert mock_get_pull_request.call_count == 2
    mock_get_checks.assert_called_once_with(repo=publication.repository, ref="headsha")
    mock_merge_pull_request.assert_called_once_with(
        repo=publication.repository, number=1, sha="headsha"
    )
    assert publication.phase == PublicationPhase.RELEASE.value
    assert publication.merge_commit_sha == "mergedsha"
    assert "Pull request merged" in publication.events[-1]


def test_advance_release_without_merge_commit(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = create_publication(
        status="running",
        phase=PublicationPhase.RELEASE.value,
        merge_commit_sha=None,
    )

    assert db_publication.advance_publication(publication)

    assert publication.status == "failure"
    assert publication.error == "Publication has no merged commit"


def test_advance_release_value_error(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = create_publication(
        status="running",
        phase=PublicationPhase.RELEASE.value,
        merge_commit_sha="mergedsha",
    )
    error = ValueError("Unable to find a free tag for 'phet_2026.05'")

    with patch.object(
        github_client, "create_release_on_sha", side_effect=error
    ) as mock_create_release_on_sha:
        assert db_publication.advance_publication(publication)

    mock_create_release_on_sha.assert_called_once_with(
        repo=publication.repository,
        app_name=publication.app_name,
        content_version=publication.content_version,
        sha="mergedsha",
        workflow=publication.workflow,
    )
    assert publication.status == "failure"
    assert publication.error == "Unable to find a free tag for 'phet_2026.05'"


def test_advance_release_success(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = create_publication(
        status="running",
        phase=PublicationPhase.RELEASE.value,
        merge_commit_sha="mergedsha",
    )
    result = PublicationResult(
        tag="phet_2026.05.0",
        commit_sha="mergedsha",
        release_id=9,
        release_url="https://github.test/release/9",
        repository=publication.repository,
        workflow=publication.workflow,
    )

    with patch.object(
        github_client, "create_release_on_sha", return_value=result
    ) as mock_create_release_on_sha:
        assert db_publication.advance_publication(publication)

    mock_create_release_on_sha.assert_called_once_with(
        repo=publication.repository,
        app_name=publication.app_name,
        content_version=publication.content_version,
        sha="mergedsha",
        workflow=publication.workflow,
    )
    assert publication.tag == "phet_2026.05.0"
    assert publication.release_id == 9
    assert publication.release_url == "https://github.test/release/9"
    assert publication.phase == PublicationPhase.BUILDING.value
    assert publication.events[-1].endswith(
        "Release phet_2026.05.0 created - https://github.test/release/9"
    )


def _building_publication(
    create_publication: Callable[..., ApplicationPublication],
    **kwargs: Any,
) -> ApplicationPublication:
    params: dict[str, Any] = {
        "status": "running",
        "phase": PublicationPhase.BUILDING.value,
        "tag": "phet_2026.05.0",
        "merge_commit_sha": "mergedsha",
        "run_id": 55,
        "run_url": "https://github.test/run/55",
    }
    params.update(kwargs)
    return create_publication(**params)


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
            PublicationPhase.STORE.value,
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
            PublicationPhase.BUILDING.value,
            None,
            id="in-progress",
        ),
    ],
)
def test_advance_building_run_states(
    create_publication: Callable[..., ApplicationPublication],
    run: dict[str, Any],
    expected_status: str,
    expected_phase: str | None,
    expected_error: str | None,
) -> None:
    publication = _building_publication(create_publication)

    with (
        patch.object(
            github_client, "get_workflow_run", return_value=run
        ) as mock_get_workflow_run,
        patch.object(
            github_client, "get_run_for_publication"
        ) as mock_get_run_for_publication,
    ):
        assert db_publication.advance_publication(publication)

    mock_get_workflow_run.assert_called_once_with(
        repo=publication.repository, run_id=55
    )
    mock_get_run_for_publication.assert_not_called()
    assert publication.status == expected_status
    assert publication.phase == expected_phase
    assert publication.error == expected_error


def test_advance_building_waits_for_run(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = _building_publication(create_publication, run_id=None, run_url=None)

    with patch.object(
        github_client, "get_run_for_publication", return_value=None
    ) as mock_get_run_for_publication:
        assert db_publication.advance_publication(publication)

    mock_get_run_for_publication.assert_called_once_with(
        repo=publication.repository,
        workflow=publication.workflow,
        tag="phet_2026.05.0",
        commit_sha="mergedsha",
    )
    assert publication.phase == PublicationPhase.BUILDING.value
    assert publication.status == "running"
    assert publication.run_id is None


def test_advance_publication_store_phase(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = create_publication(
        status="running", phase=PublicationPhase.STORE.value
    )

    assert db_publication.advance_publication(publication)

    assert publication.status == "success"
    assert publication.phase is None
    assert publication.phase_started_at is None
    assert publication.events[-1].endswith("Uploaded to android; awaiting store review")


def test_advance_publication_requested_is_not_advanced(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = create_publication(
        status="pending", phase=PublicationPhase.REQUESTED.value
    )

    assert not db_publication.advance_publication(publication)
    assert publication.phase == PublicationPhase.REQUESTED.value


def test_start_publication_value_error(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = create_publication(
        status="pending", phase=PublicationPhase.REQUESTED.value
    )
    error = ValueError(
        "Unable to find 'phet/info.json' in 'kiwix/kiwix-android-branded'"
    )

    with patch.object(
        github_client, "create_publication_pull_request", side_effect=error
    ) as mock_create_pull_request:
        result = db_publication.start_publication(publication)

    mock_create_pull_request.assert_called_once_with(
        store="android",
        app_name="phet",
        content_version="2026-05",
        zim_filename="phet_mul_all_maxi_2026-05.zim",
        branch="cms/publication-test",
        publication_id=str(publication.id),
    )
    assert result is publication
    assert publication.status == "failure"
    assert (
        publication.error
        == "Unable to find 'phet/info.json' in 'kiwix/kiwix-android-branded'"
    )


def test_start_publication_without_changes(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = create_publication(
        status="pending", phase=PublicationPhase.REQUESTED.value
    )
    pull_request_result = PublicationPullRequestResult(
        branch="main", base_sha="basesha", pr_number=None, pr_url=None
    )

    with patch.object(
        github_client,
        "create_publication_pull_request",
        return_value=pull_request_result,
    ) as mock_create_pull_request:
        result = db_publication.start_publication(publication)

    mock_create_pull_request.assert_called_once_with(
        store="android",
        app_name="phet",
        content_version="2026-05",
        zim_filename="phet_mul_all_maxi_2026-05.zim",
        branch="cms/publication-test",
        publication_id=str(publication.id),
    )
    assert result is publication
    assert publication.branch == "main"
    assert publication.commit_sha == "basesha"
    assert publication.merge_commit_sha == "basesha"
    assert publication.pr_number is None
    assert publication.phase == PublicationPhase.RELEASE.value
    assert "Configuration already up to date" in publication.events[-1]


def test_start_publication_opens_pull_request(
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = create_publication(
        status="pending", phase=PublicationPhase.REQUESTED.value
    )
    pull_request_result = PublicationPullRequestResult(
        branch="cms/publication-test",
        base_sha="basesha",
        pr_number=12,
        pr_url="https://github.test/pr/12",
    )

    with patch.object(
        github_client,
        "create_publication_pull_request",
        return_value=pull_request_result,
    ) as mock_create_pull_request:
        result = db_publication.start_publication(publication)

    mock_create_pull_request.assert_called_once_with(
        store="android",
        app_name="phet",
        content_version="2026-05",
        zim_filename="phet_mul_all_maxi_2026-05.zim",
        branch="cms/publication-test",
        publication_id=str(publication.id),
    )
    assert result is publication
    assert publication.branch == "cms/publication-test"
    assert publication.commit_sha == "basesha"
    assert publication.pr_number == 12
    assert publication.pr_url == "https://github.test/pr/12"
    assert publication.phase == PublicationPhase.CHECKS.value
    assert publication.status == "running"
    assert "Configuration changes prepared" in publication.events[-2]
    assert "Pull request opened" in publication.events[-1]
