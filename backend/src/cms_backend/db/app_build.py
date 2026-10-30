from typing import Any, cast
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend import logger
from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import (
    Account,
    AppBuildPhase,
    ApplicationBuild,
)
from cms_backend.schemas.models import ApplicationBuildCreateSchema
from cms_backend.schemas.orms import ApplicationBuildSchema, ListResult
from cms_backend.utils.datetime import getnow
from cms_backend.utils.github import get_tag_prefix, github_client

TERMINAL_STATUSES = {"success", "failure", "cancelled"}
ACTIVE_STATUSES = {"pending", "running"}


def _app_build_label(build: ApplicationBuild) -> str:
    """Contextual prefix for build log lines."""
    return (
        f"build {build.id} [{build.app_name}/"
        f"{build.store}, content {build.content_version}]"
    )


def create_app_build(
    session: OrmSession,
    *,
    payload: ApplicationBuildCreateSchema,
) -> ApplicationBuild:
    now = getnow()
    build = ApplicationBuild(
        application_id=payload.application_id,
        store=payload.store,
        content_version=payload.content_version,
        app_name=payload.app_name,
        tag=payload.tag,
        commit_sha=payload.commit_sha,
        repository=payload.repository,
        workflow=payload.workflow,
        branch=payload.branch,
        zim_filename=payload.zim_filename,
        release_id=payload.release_id,
        release_url=payload.release_url,
        requested_by_id=payload.requested_by_id,
        status="pending",
        phase=AppBuildPhase.REQUESTED.value,
        phase_started_at=now,
    )
    build.events.append(f"{now}: Build requested")
    session.add(build)
    session.flush()
    logger.info(
        f"{_app_build_label(build)} requested for repository "
        f"'{build.repository}' on branch '{build.branch}'"
    )
    return build


def get_app_build_or_none(
    session: OrmSession, *, build_id: UUID
) -> ApplicationBuild | None:
    return session.scalars(
        select(ApplicationBuild)
        .where(
            ApplicationBuild.id == build_id,
        )
        .options(
            selectinload(ApplicationBuild.application),
            selectinload(ApplicationBuild.requested_by),
            selectinload(ApplicationBuild.cancelled_by),
        )
    ).one_or_none()


def get_build(session: OrmSession, *, build_id: UUID) -> ApplicationBuild:
    build = get_app_build_or_none(session, build_id=build_id)
    if build is None:
        raise RecordDoesNotExistError(f"Build {build_id} does not exist")
    return build


def get_active_app_build_or_none(
    session: OrmSession,
    *,
    application_id: UUID,
) -> ApplicationBuild | None:
    """Get a build for this app which has not reached a terminal status."""
    return session.scalars(
        select(ApplicationBuild)
        .where(
            ApplicationBuild.application_id == application_id,
            ApplicationBuild.status.in_(ACTIVE_STATUSES),
        )
        .limit(1)
    ).one_or_none()


def get_app_builds_in_progress(
    session: OrmSession,
) -> list[ApplicationBuild]:
    """Get builds the mill should advance."""
    return list(
        session.scalars(
            select(ApplicationBuild)
            .where(
                ApplicationBuild.status.in_(ACTIVE_STATUSES),
                ApplicationBuild.phase.in_(
                    [
                        AppBuildPhase.CHECKS.value,
                        AppBuildPhase.MERGE.value,
                        AppBuildPhase.RELEASE.value,
                        AppBuildPhase.BUILDING.value,
                        AppBuildPhase.UPLOADED.value,
                    ]
                ),
            )
            .order_by(ApplicationBuild.updated_at)
        ).all()
    )


def get_successful_app_build_for_content(
    session: OrmSession,
    *,
    application_id: UUID,
    app_name: str,
    content_version: str,
) -> ApplicationBuild | None:
    """Get the latest successful build of this content version."""
    base_tag = get_tag_prefix(app_name=app_name, content_version=content_version)
    return session.scalars(
        select(ApplicationBuild)
        .where(
            ApplicationBuild.application_id == application_id,
            ApplicationBuild.status == "success",
            or_(
                ApplicationBuild.tag == base_tag,
                ApplicationBuild.tag.startswith(f"{base_tag}.", autoescape=True),
            ),
        )
        .options(selectinload(ApplicationBuild.application))
        .order_by(ApplicationBuild.created_at.desc())
        .limit(1)
    ).one_or_none()


def get_app_builds(
    session: OrmSession,
    *,
    application_id: UUID | None = None,
    store: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> ListResult[ApplicationBuildSchema]:
    stmt = (
        select(ApplicationBuild)
        .where(
            (ApplicationBuild.application_id == application_id)
            | (application_id is None),
            (ApplicationBuild.store == store) | (store is None),
        )
        .options(
            selectinload(ApplicationBuild.application),
            selectinload(ApplicationBuild.requested_by),
            selectinload(ApplicationBuild.cancelled_by),
        )
    )
    records = session.scalars(
        stmt.order_by(ApplicationBuild.created_at.desc()).offset(skip).limit(limit)
    ).all()

    return ListResult[ApplicationBuildSchema](
        nb_records=count_from_stmt(session, stmt),
        records=[create_app_build_schema(build) for build in records],
    )


def create_app_build_schema(
    build: ApplicationBuild,
) -> ApplicationBuildSchema:
    return ApplicationBuildSchema(
        id=build.id,
        title_id=build.application.title_id,
        flavour=build.application.flavour,
        store=build.store,
        repository=build.repository,
        app_name=build.app_name,
        status=build.status,
        phase=build.phase,
        phase_started_at=build.phase_started_at,
        content_version=build.content_version,
        tag=build.tag,
        branch=build.branch,
        pr_number=build.pr_number,
        pr_url=build.pr_url,
        merge_commit_sha=build.merge_commit_sha,
        release_url=build.release_url,
        run_url=build.run_url,
        error=build.error,
        events=build.events,
        requested_by=(build.requested_by.username if build.requested_by else None),
        cancelled_by=(build.cancelled_by.display_name if build.cancelled_by else None),
        created_at=build.created_at,
        updated_at=build.updated_at,
    )


def _set_phase(build: ApplicationBuild, phase: AppBuildPhase) -> None:
    previous_phase = build.phase
    build.phase = phase.value
    build.phase_started_at = getnow()
    build.status = "running"
    build.error = None
    logger.info(
        f"{_app_build_label(build)} moved from phase "
        f"'{previous_phase or 'none'}' to '{phase.value}'"
    )


def cancel_app_build(
    session: OrmSession,
    build: ApplicationBuild,
    *,
    cancelled_by: Account,
) -> ApplicationBuild:
    """Cancel a build and best-effort stop its GitHub side effects."""
    if build.pr_number is not None and build.merge_commit_sha is None:
        try:
            github_client.close_pull_request(
                repo=build.repository, number=build.pr_number
            )
        except Exception:
            logger.exception(
                f"Unable to close pull request #{build.pr_number} for build {build.id}"
            )

    run_id = build.run_id
    if run_id is None and build.tag and build.merge_commit_sha:
        try:
            run = github_client.get_run_for_build(
                repo=build.repository,
                workflow=build.workflow,
                tag=build.tag,
                commit_sha=build.merge_commit_sha,
            )
            if run is not None:
                run_id = cast(int, run.get("id"))
        except Exception:
            logger.exception(f"Unable to find workflow run for build {build.id}")

    if run_id is not None:
        try:
            github_client.cancel_workflow_run(repo=build.repository, run_id=run_id)
        except Exception:
            logger.exception(
                f"Unable to cancel workflow run {run_id} for build {build.id}"
            )

    build.phase = None
    build.phase_started_at = None
    build.status = "cancelled"
    build.cancelled_by = cancelled_by
    build.events.append(f"{getnow()}: cancelled by {cancelled_by.display_name}")
    logger.info(f"{_app_build_label(build)} cancelled by {cancelled_by.display_name}")
    session.flush()
    return build


def fail_app_build(build: ApplicationBuild, message: str) -> None:
    phase = build.phase
    build.phase = None
    build.phase_started_at = None
    build.status = "failure"
    build.error = message
    url = build.pr_url or build.run_url
    build.events.append(f"{getnow()}: {message}" + (f" - {url}" if url else ""))
    logger.error(
        f"{_app_build_label(build)} failed during phase "
        f"'{phase or 'none'}': {message}" + (f" - {url}" if url else "")
    )


def _record_merged(build: ApplicationBuild, pull: dict[str, Any]) -> None:
    build.merge_commit_sha = pull.get("merge_commit_sha")
    build.events.append(
        f"{getnow()}: Pull request merged"
        + (f" - {build.pr_url}" if build.pr_url else "")
    )
    logger.info(
        f"{_app_build_label(build)} pull request "
        f"#{build.pr_number} merged at commit "
        f"{build.merge_commit_sha}"
    )


def _advance_checks(build: ApplicationBuild) -> None:
    if build.pr_number is None:
        fail_app_build(build, "Build has no pull request")
        return

    pull = github_client.get_pull_request(repo=build.repository, number=build.pr_number)
    if pull is None:
        logger.debug(
            f"{_app_build_label(build)} pull request "
            f"#{build.pr_number} is not available yet"
        )
        return

    if pull.get("merged"):
        _record_merged(build, pull)
        _set_phase(build, AppBuildPhase.RELEASE)
        return

    head = cast(dict[str, Any], pull.get("head") or {})
    head_sha = head.get("sha")
    if not isinstance(head_sha, str) or not head_sha:
        fail_app_build(build, "Unable to determine pull request head commit")
        return

    checks = github_client.get_checks(repo=build.repository, ref=head_sha)
    if checks.failed:
        fail_app_build(
            build,
            f"Pull request checks failed: {', '.join(checks.failed)}",
        )
        return
    if checks.pending:
        logger.debug(
            f"{_app_build_label(build)} waiting for "
            f"{checks.pending} pending check(s) on pull request "
            f"#{build.pr_number} ({checks.passed}/{checks.total} passed)"
        )
        return

    if pull.get("mergeable") is False or pull.get("mergeable_state") == "dirty":
        fail_app_build(build, "Pull request cannot be merged")
        return

    logger.info(
        f"{_app_build_label(build)} checks passed on pull request "
        f"#{build.pr_number} ({checks.passed}/{checks.total})"
    )
    checks_url = f"{build.pr_url}/checks" if build.pr_url else None
    build.events.append(
        f"{getnow()}: Pull request checks passed"
        + (f" - {checks_url}" if checks_url else "")
    )
    _set_phase(build, AppBuildPhase.MERGE)


def _advance_merge(build: ApplicationBuild) -> None:
    if build.pr_number is None:
        fail_app_build(build, "Build has no pull request")
        return

    pull = github_client.get_pull_request(repo=build.repository, number=build.pr_number)
    if pull is None:
        logger.debug(
            f"{_app_build_label(build)} pull request "
            f"#{build.pr_number} is not available yet"
        )
        return

    if pull.get("merged"):
        _record_merged(build, pull)
        _set_phase(build, AppBuildPhase.RELEASE)
        return

    head = cast(dict[str, Any], pull.get("head") or {})
    head_sha = head.get("sha")
    if not isinstance(head_sha, str) or not head_sha:
        fail_app_build(build, "Unable to determine pull request head commit")
        return

    checks = github_client.get_checks(repo=build.repository, ref=head_sha)
    if checks.failed:
        fail_app_build(
            build,
            f"Pull request checks failed: {', '.join(checks.failed)}",
        )
        return
    if checks.pending:
        logger.debug(
            f"{_app_build_label(build)} waiting for "
            f"{checks.pending} pending check(s) before merging pull request "
            f"#{build.pr_number}"
        )
        return

    if pull.get("mergeable") is False or pull.get("mergeable_state") in {
        "dirty",
        "blocked",
    }:
        fail_app_build(build, "Pull request cannot be merged")
        return

    logger.info(
        f"{_app_build_label(build)} merging pull request "
        f"#{build.pr_number} at commit {head_sha}"
    )
    if not github_client.merge_pull_request(
        repo=build.repository, number=build.pr_number, sha=head_sha
    ):
        logger.warning(
            f"{_app_build_label(build)} merge of pull request "
            f"#{build.pr_number} was not accepted; will retry"
        )
        return

    pull = github_client.get_pull_request(repo=build.repository, number=build.pr_number)
    if pull is not None and pull.get("merged"):
        _record_merged(build, pull)
        _set_phase(build, AppBuildPhase.RELEASE)
    else:
        logger.debug(
            f"{_app_build_label(build)} merge accepted for pull "
            f"request #{build.pr_number}; waiting for GitHub to report it"
        )


def _advance_release(build: ApplicationBuild) -> None:
    if not build.merge_commit_sha:
        fail_app_build(build, "Build has no merged commit")
        return

    logger.info(
        f"{_app_build_label(build)} creating release from merge "
        f"commit {build.merge_commit_sha}"
    )
    try:
        result = github_client.create_release_on_sha(
            repo=build.repository,
            app_name=build.app_name,
            content_version=build.content_version,
            sha=build.merge_commit_sha,
            workflow=build.workflow,
        )
    except ValueError as exc:
        fail_app_build(build, str(exc))
        return

    build.tag = result.tag
    build.release_id = result.release_id
    build.release_url = result.release_url
    build.events.append(
        f"{getnow()}: Release {result.tag} created - {result.release_url}"
    )
    logger.info(
        f"{_app_build_label(build)} release '{result.tag}' created - "
        f"{result.release_url}"
    )
    _set_phase(build, AppBuildPhase.BUILDING)


def _advance_building(build: ApplicationBuild) -> None:
    run: dict[str, Any] | None = None
    if build.run_id is not None:
        run = github_client.get_workflow_run(repo=build.repository, run_id=build.run_id)
    if run is None:
        run = github_client.get_run_for_build(
            repo=build.repository,
            workflow=build.workflow,
            tag=build.tag or "",
            commit_sha=build.merge_commit_sha or "",
        )
        if run is not None:
            build.run_id = run.get("id")
            build.run_url = run.get("html_url")
            logger.info(
                f"{_app_build_label(build)} found workflow run "
                f"{build.run_id} for tag '{build.tag}' - "
                f"{build.run_url}"
            )

    if run is None:
        logger.debug(
            f"{_app_build_label(build)} workflow run for tag "
            f"'{build.tag}' not found yet"
        )
        return

    run_status = run.get("status")
    conclusion = run.get("conclusion")
    if run_status == "completed":
        if conclusion == "success":
            build.events.append(
                f"{getnow()}: Build and upload to {build.store} completed"
                + (f" - {build.run_url}" if build.run_url else "")
            )
            logger.info(
                f"{_app_build_label(build)} workflow run {build.run_id} succeeded"
            )
            _set_phase(build, AppBuildPhase.UPLOADED)
        elif conclusion == "cancelled":
            build.phase = None
            build.phase_started_at = None
            build.status = "cancelled"
            build.events.append(
                f"{getnow()}: Build cancelled"
                + (f" - {build.run_url}" if build.run_url else "")
            )
            logger.warning(
                f"{_app_build_label(build)} workflow run {build.run_id} was cancelled"
            )
        else:
            fail_app_build(build, f"Build failed: {conclusion or 'workflow failed'}")


def _advance_uploaded(build: ApplicationBuild) -> None:
    build.events.append(f"{getnow()}: Uploaded to {build.store}; awaiting store review")
    build.phase = None
    build.phase_started_at = None
    build.status = "success"
    build.error = None
    logger.info(f"{_app_build_label(build)} completed: uploaded to {build.store}")


def start_app_build(build: ApplicationBuild) -> ApplicationBuild:
    """Prepare configuration changes and open the build pull request."""
    if build.phase != AppBuildPhase.REQUESTED.value:
        return build

    logger.info(
        f"{_app_build_label(build)} starting: preparing configuration "
        f"for '{build.app_name}' in '{build.repository}'"
    )
    try:
        result = github_client.create_app_build_pull_request(
            store=build.store,
            app_name=build.app_name,
            content_version=build.content_version,
            zim_filename=build.zim_filename,
            branch=build.branch,
            build_id=str(build.id),
        )
    except ValueError as exc:
        fail_app_build(build, str(exc))
        return build

    build.branch = result.branch
    build.commit_sha = result.base_sha
    if result.pr_number is None:
        build.merge_commit_sha = result.base_sha
        build.events.append(
            f"{getnow()}: Configuration already up to date; "
            "skipping pull request and creating a new release"
        )
        logger.info(
            f"{_app_build_label(build)} configuration already up to "
            f"date at commit {result.base_sha}; skipping pull request"
        )
        _set_phase(build, AppBuildPhase.RELEASE)
        return build

    build.pr_number = result.pr_number
    build.pr_url = result.pr_url
    build.events.append(f"{getnow()}: Configuration changes prepared")
    build.events.append(f"{getnow()}: Pull request opened - {result.pr_url}")
    logger.info(
        f"{_app_build_label(build)} opened pull request "
        f"#{result.pr_number} on branch '{result.branch}' - {result.pr_url}"
    )
    _set_phase(build, AppBuildPhase.CHECKS)
    return build


def advance_app_build(build: ApplicationBuild) -> bool:
    """Advance a build by one phase. Returns True when it was processed."""
    if build.status in TERMINAL_STATUSES or build.phase is None:
        return False

    phase = build.phase
    if phase == AppBuildPhase.REQUESTED.value:
        # Starting is handled by the build request event processor.
        return False

    logger.debug(f"{_app_build_label(build)} advancing phase '{phase}'")
    if phase == AppBuildPhase.CHECKS.value:
        _advance_checks(build)
    elif phase == AppBuildPhase.MERGE.value:
        _advance_merge(build)
    elif phase == AppBuildPhase.RELEASE.value:
        _advance_release(build)
    elif phase == AppBuildPhase.BUILDING.value:
        _advance_building(build)
    elif phase == AppBuildPhase.UPLOADED.value:
        _advance_uploaded(build)
    else:
        fail_app_build(build, f"Unknown build phase '{phase}'")

    return True
