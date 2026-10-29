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
    ApplicationPublication,
    PublicationPhase,
)
from cms_backend.schemas.models import ApplicationPublicationCreateSchema
from cms_backend.schemas.orms import ApplicationPublicationSchema, ListResult
from cms_backend.utils.datetime import getnow
from cms_backend.utils.github import get_tag_prefix, github_client

TERMINAL_STATUSES = {"success", "failure", "cancelled"}
ACTIVE_STATUSES = {"pending", "running"}


def _publication_label(publication: ApplicationPublication) -> str:
    """Contextual prefix for publication log lines."""
    return (
        f"publication {publication.id} [{publication.app_name}/"
        f"{publication.store}, content {publication.content_version}]"
    )


def create_publication(
    session: OrmSession,
    *,
    payload: ApplicationPublicationCreateSchema,
) -> ApplicationPublication:
    now = getnow()
    publication = ApplicationPublication(
        title_id=payload.title_id,
        flavour=payload.flavour,
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
        phase=PublicationPhase.REQUESTED.value,
        phase_started_at=now,
    )
    publication.events.append(f"{now}: Publication requested")
    session.add(publication)
    session.flush()
    logger.info(
        f"{_publication_label(publication)} requested for repository "
        f"'{publication.repository}' on branch '{publication.branch}'"
    )
    return publication


def get_publication_or_none(
    session: OrmSession, *, publication_id: UUID
) -> ApplicationPublication | None:
    return session.scalars(
        select(ApplicationPublication)
        .where(
            ApplicationPublication.id == publication_id,
        )
        .options(
            selectinload(ApplicationPublication.requested_by),
            selectinload(ApplicationPublication.cancelled_by),
        )
    ).one_or_none()


def get_publication(
    session: OrmSession, *, publication_id: UUID
) -> ApplicationPublication:
    publication = get_publication_or_none(session, publication_id=publication_id)
    if publication is None:
        raise RecordDoesNotExistError(f"Publication {publication_id} does not exist")
    return publication


def get_active_publication_or_none(
    session: OrmSession,
    *,
    title_id: UUID,
    flavour: str,
    store: str,
) -> ApplicationPublication | None:
    """Get a publication for this app which has not reached a terminal status."""
    return session.scalars(
        select(ApplicationPublication)
        .where(
            ApplicationPublication.title_id == title_id,
            ApplicationPublication.flavour == flavour,
            ApplicationPublication.store == store,
            ApplicationPublication.status.in_(ACTIVE_STATUSES),
        )
        .limit(1)
    ).one_or_none()


def get_publications_in_progress(
    session: OrmSession,
) -> list[ApplicationPublication]:
    """Get publications the mill should advance."""
    return list(
        session.scalars(
            select(ApplicationPublication)
            .where(
                ApplicationPublication.status.in_(ACTIVE_STATUSES),
                ApplicationPublication.phase.in_(
                    [
                        PublicationPhase.CHECKS.value,
                        PublicationPhase.MERGE.value,
                        PublicationPhase.RELEASE.value,
                        PublicationPhase.BUILDING.value,
                        PublicationPhase.STORE.value,
                    ]
                ),
            )
            .order_by(ApplicationPublication.updated_at)
        ).all()
    )


def get_successful_publication_for_content(
    session: OrmSession,
    *,
    title_id: UUID,
    flavour: str,
    store: str,
    app_name: str,
    content_version: str,
) -> ApplicationPublication | None:
    """Get the latest successful publication of this content version."""
    base_tag = get_tag_prefix(app_name=app_name, content_version=content_version)
    return session.scalars(
        select(ApplicationPublication)
        .where(
            ApplicationPublication.title_id == title_id,
            ApplicationPublication.flavour == flavour,
            ApplicationPublication.store == store,
            ApplicationPublication.status == "success",
            or_(
                ApplicationPublication.tag == base_tag,
                ApplicationPublication.tag.startswith(f"{base_tag}.", autoescape=True),
            ),
        )
        .order_by(ApplicationPublication.created_at.desc())
        .limit(1)
    ).one_or_none()


def get_publications(
    session: OrmSession,
    *,
    title_id: UUID | None = None,
    flavour: str | None = None,
    store: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> ListResult[ApplicationPublicationSchema]:
    stmt = (
        select(ApplicationPublication)
        .where(
            (ApplicationPublication.title_id == title_id) | (title_id is None),
            (ApplicationPublication.flavour == flavour) | (flavour is None),
            (ApplicationPublication.store == store) | (store is None),
        )
        .options(
            selectinload(ApplicationPublication.requested_by),
            selectinload(ApplicationPublication.cancelled_by),
        )
    )
    records = session.scalars(
        stmt.order_by(ApplicationPublication.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    return ListResult[ApplicationPublicationSchema](
        nb_records=count_from_stmt(session, stmt),
        records=[create_publication_schema(publication) for publication in records],
    )


def create_publication_schema(
    publication: ApplicationPublication,
) -> ApplicationPublicationSchema:
    return ApplicationPublicationSchema(
        id=publication.id,
        title_id=publication.title_id,
        flavour=publication.flavour,
        store=publication.store,
        repository=publication.repository,
        app_name=publication.app_name,
        status=publication.status,
        phase=publication.phase,
        phase_started_at=publication.phase_started_at,
        content_version=publication.content_version,
        tag=publication.tag,
        branch=publication.branch,
        pr_number=publication.pr_number,
        pr_url=publication.pr_url,
        merge_commit_sha=publication.merge_commit_sha,
        release_url=publication.release_url,
        run_url=publication.run_url,
        error=publication.error,
        events=publication.events,
        requested_by=(
            publication.requested_by.username if publication.requested_by else None
        ),
        cancelled_by=(
            publication.cancelled_by.display_name if publication.cancelled_by else None
        ),
        created_at=publication.created_at,
        updated_at=publication.updated_at,
    )


def _set_phase(publication: ApplicationPublication, phase: PublicationPhase) -> None:
    previous_phase = publication.phase
    publication.phase = phase.value
    publication.phase_started_at = getnow()
    publication.status = "running"
    publication.error = None
    logger.info(
        f"{_publication_label(publication)} moved from phase "
        f"'{previous_phase or 'none'}' to '{phase.value}'"
    )


def cancel_publication(
    session: OrmSession,
    publication: ApplicationPublication,
    *,
    cancelled_by: Account,
) -> ApplicationPublication:
    """Cancel a publication and best-effort stop its GitHub side effects."""
    if publication.pr_number is not None and publication.merge_commit_sha is None:
        try:
            github_client.close_pull_request(
                repo=publication.repository, number=publication.pr_number
            )
        except Exception:
            logger.exception(
                f"Unable to close pull request #{publication.pr_number} "
                f"for publication {publication.id}"
            )

    run_id = publication.run_id
    if run_id is None and publication.tag and publication.merge_commit_sha:
        try:
            run = github_client.get_run_for_publication(
                repo=publication.repository,
                workflow=publication.workflow,
                tag=publication.tag,
                commit_sha=publication.merge_commit_sha,
            )
            if run is not None:
                run_id = cast(int, run.get("id"))
        except Exception:
            logger.exception(
                f"Unable to find workflow run for publication {publication.id}"
            )

    if run_id is not None:
        try:
            github_client.cancel_workflow_run(
                repo=publication.repository, run_id=run_id
            )
        except Exception:
            logger.exception(
                f"Unable to cancel workflow run {run_id} "
                f"for publication {publication.id}"
            )

    publication.phase = None
    publication.phase_started_at = None
    publication.status = "cancelled"
    publication.cancelled_by = cancelled_by
    publication.events.append(f"{getnow()}: cancelled by {cancelled_by.display_name}")
    logger.info(
        f"{_publication_label(publication)} cancelled by {cancelled_by.display_name}"
    )
    session.flush()
    return publication


def fail_publication(publication: ApplicationPublication, message: str) -> None:
    phase = publication.phase
    publication.phase = None
    publication.phase_started_at = None
    publication.status = "failure"
    publication.error = message
    url = publication.pr_url or publication.run_url
    publication.events.append(f"{getnow()}: {message}" + (f" - {url}" if url else ""))
    logger.error(
        f"{_publication_label(publication)} failed during phase "
        f"'{phase or 'none'}': {message}" + (f" - {url}" if url else "")
    )


def _record_merged(publication: ApplicationPublication, pull: dict[str, Any]) -> None:
    publication.merge_commit_sha = pull.get("merge_commit_sha")
    publication.events.append(
        f"{getnow()}: Pull request merged"
        + (f" - {publication.pr_url}" if publication.pr_url else "")
    )
    logger.info(
        f"{_publication_label(publication)} pull request "
        f"#{publication.pr_number} merged at commit "
        f"{publication.merge_commit_sha}"
    )


def _advance_checks(publication: ApplicationPublication) -> None:
    if publication.pr_number is None:
        fail_publication(publication, "Publication has no pull request")
        return

    pull = github_client.get_pull_request(
        repo=publication.repository, number=publication.pr_number
    )
    if pull is None:
        logger.debug(
            f"{_publication_label(publication)} pull request "
            f"#{publication.pr_number} is not available yet"
        )
        return

    if pull.get("merged"):
        _record_merged(publication, pull)
        _set_phase(publication, PublicationPhase.RELEASE)
        return

    head = cast(dict[str, Any], pull.get("head") or {})
    head_sha = head.get("sha")
    if not isinstance(head_sha, str) or not head_sha:
        fail_publication(publication, "Unable to determine pull request head commit")
        return

    checks = github_client.get_checks(repo=publication.repository, ref=head_sha)
    if checks.failed:
        fail_publication(
            publication,
            f"Pull request checks failed: {', '.join(checks.failed)}",
        )
        return
    if checks.pending:
        logger.debug(
            f"{_publication_label(publication)} waiting for "
            f"{checks.pending} pending check(s) on pull request "
            f"#{publication.pr_number} ({checks.passed}/{checks.total} passed)"
        )
        return

    if pull.get("mergeable") is False or pull.get("mergeable_state") == "dirty":
        fail_publication(publication, "Pull request cannot be merged")
        return

    logger.info(
        f"{_publication_label(publication)} checks passed on pull request "
        f"#{publication.pr_number} ({checks.passed}/{checks.total})"
    )
    checks_url = f"{publication.pr_url}/checks" if publication.pr_url else None
    publication.events.append(
        f"{getnow()}: Pull request checks passed"
        + (f" - {checks_url}" if checks_url else "")
    )
    _set_phase(publication, PublicationPhase.MERGE)


def _advance_merge(publication: ApplicationPublication) -> None:
    if publication.pr_number is None:
        fail_publication(publication, "Publication has no pull request")
        return

    pull = github_client.get_pull_request(
        repo=publication.repository, number=publication.pr_number
    )
    if pull is None:
        logger.debug(
            f"{_publication_label(publication)} pull request "
            f"#{publication.pr_number} is not available yet"
        )
        return

    if pull.get("merged"):
        _record_merged(publication, pull)
        _set_phase(publication, PublicationPhase.RELEASE)
        return

    head = cast(dict[str, Any], pull.get("head") or {})
    head_sha = head.get("sha")
    if not isinstance(head_sha, str) or not head_sha:
        fail_publication(publication, "Unable to determine pull request head commit")
        return

    checks = github_client.get_checks(repo=publication.repository, ref=head_sha)
    if checks.failed:
        fail_publication(
            publication,
            f"Pull request checks failed: {', '.join(checks.failed)}",
        )
        return
    if checks.pending:
        logger.debug(
            f"{_publication_label(publication)} waiting for "
            f"{checks.pending} pending check(s) before merging pull request "
            f"#{publication.pr_number}"
        )
        return

    if pull.get("mergeable") is False or pull.get("mergeable_state") in {
        "dirty",
        "blocked",
    }:
        fail_publication(publication, "Pull request cannot be merged")
        return

    logger.info(
        f"{_publication_label(publication)} merging pull request "
        f"#{publication.pr_number} at commit {head_sha}"
    )
    if not github_client.merge_pull_request(
        repo=publication.repository, number=publication.pr_number, sha=head_sha
    ):
        logger.warning(
            f"{_publication_label(publication)} merge of pull request "
            f"#{publication.pr_number} was not accepted; will retry"
        )
        return

    pull = github_client.get_pull_request(
        repo=publication.repository, number=publication.pr_number
    )
    if pull is not None and pull.get("merged"):
        _record_merged(publication, pull)
        _set_phase(publication, PublicationPhase.RELEASE)
    else:
        logger.debug(
            f"{_publication_label(publication)} merge accepted for pull "
            f"request #{publication.pr_number}; waiting for GitHub to report it"
        )


def _advance_release(publication: ApplicationPublication) -> None:
    if not publication.merge_commit_sha:
        fail_publication(publication, "Publication has no merged commit")
        return

    logger.info(
        f"{_publication_label(publication)} creating release from merge "
        f"commit {publication.merge_commit_sha}"
    )
    try:
        result = github_client.create_release_on_sha(
            repo=publication.repository,
            app_name=publication.app_name,
            content_version=publication.content_version,
            sha=publication.merge_commit_sha,
            workflow=publication.workflow,
        )
    except ValueError as exc:
        fail_publication(publication, str(exc))
        return

    publication.tag = result.tag
    publication.release_id = result.release_id
    publication.release_url = result.release_url
    publication.events.append(
        f"{getnow()}: Release {result.tag} created - {result.release_url}"
    )
    logger.info(
        f"{_publication_label(publication)} release '{result.tag}' created - "
        f"{result.release_url}"
    )
    _set_phase(publication, PublicationPhase.BUILDING)


def _advance_building(publication: ApplicationPublication) -> None:
    run: dict[str, Any] | None = None
    if publication.run_id is not None:
        run = github_client.get_workflow_run(
            repo=publication.repository, run_id=publication.run_id
        )
    if run is None:
        run = github_client.get_run_for_publication(
            repo=publication.repository,
            workflow=publication.workflow,
            tag=publication.tag or "",
            commit_sha=publication.merge_commit_sha or "",
        )
        if run is not None:
            publication.run_id = run.get("id")
            publication.run_url = run.get("html_url")
            logger.info(
                f"{_publication_label(publication)} found workflow run "
                f"{publication.run_id} for tag '{publication.tag}' - "
                f"{publication.run_url}"
            )

    if run is None:
        logger.debug(
            f"{_publication_label(publication)} workflow run for tag "
            f"'{publication.tag}' not found yet"
        )
        return

    run_status = run.get("status")
    conclusion = run.get("conclusion")
    if run_status == "completed":
        if conclusion == "success":
            publication.events.append(
                f"{getnow()}: Build and upload to {publication.store} completed"
                + (f" - {publication.run_url}" if publication.run_url else "")
            )
            logger.info(
                f"{_publication_label(publication)} workflow run "
                f"{publication.run_id} succeeded"
            )
            _set_phase(publication, PublicationPhase.STORE)
        elif conclusion == "cancelled":
            publication.phase = None
            publication.phase_started_at = None
            publication.status = "cancelled"
            publication.events.append(
                f"{getnow()}: Build cancelled"
                + (f" - {publication.run_url}" if publication.run_url else "")
            )
            logger.warning(
                f"{_publication_label(publication)} workflow run "
                f"{publication.run_id} was cancelled"
            )
        else:
            fail_publication(
                publication, f"Build failed: {conclusion or 'workflow failed'}"
            )


def _advance_store(publication: ApplicationPublication) -> None:
    publication.events.append(
        f"{getnow()}: Uploaded to {publication.store}; awaiting store review"
    )
    publication.phase = None
    publication.phase_started_at = None
    publication.status = "success"
    publication.error = None
    logger.info(
        f"{_publication_label(publication)} completed: uploaded to {publication.store}"
    )


def start_publication(publication: ApplicationPublication) -> ApplicationPublication:
    """Prepare configuration changes and open the publication pull request."""
    if publication.phase != PublicationPhase.REQUESTED.value:
        return publication

    logger.info(
        f"{_publication_label(publication)} starting: preparing configuration "
        f"for '{publication.app_name}' in '{publication.repository}'"
    )
    try:
        result = github_client.create_publication_pull_request(
            store=publication.store,
            app_name=publication.app_name,
            content_version=publication.content_version,
            zim_filename=publication.zim_filename,
            branch=publication.branch,
            publication_id=str(publication.id),
        )
    except ValueError as exc:
        fail_publication(publication, str(exc))
        return publication

    publication.branch = result.branch
    publication.commit_sha = result.base_sha
    if result.pr_number is None:
        publication.merge_commit_sha = result.base_sha
        publication.events.append(
            f"{getnow()}: Configuration already up to date; "
            "skipping pull request and creating a new release"
        )
        logger.info(
            f"{_publication_label(publication)} configuration already up to "
            f"date at commit {result.base_sha}; skipping pull request"
        )
        _set_phase(publication, PublicationPhase.RELEASE)
        return publication

    publication.pr_number = result.pr_number
    publication.pr_url = result.pr_url
    publication.events.append(f"{getnow()}: Configuration changes prepared")
    publication.events.append(f"{getnow()}: Pull request opened - {result.pr_url}")
    logger.info(
        f"{_publication_label(publication)} opened pull request "
        f"#{result.pr_number} on branch '{result.branch}' - {result.pr_url}"
    )
    _set_phase(publication, PublicationPhase.CHECKS)
    return publication


def advance_publication(publication: ApplicationPublication) -> bool:
    """Advance a publication by one phase. Returns True when it was processed."""
    if publication.status in TERMINAL_STATUSES or publication.phase is None:
        return False

    phase = publication.phase
    if phase == PublicationPhase.REQUESTED.value:
        # Starting is handled by the publication request event processor.
        return False

    logger.debug(f"{_publication_label(publication)} advancing phase '{phase}'")
    if phase == PublicationPhase.CHECKS.value:
        _advance_checks(publication)
    elif phase == PublicationPhase.MERGE.value:
        _advance_merge(publication)
    elif phase == PublicationPhase.RELEASE.value:
        _advance_release(publication)
    elif phase == PublicationPhase.BUILDING.value:
        _advance_building(publication)
    elif phase == PublicationPhase.STORE.value:
        _advance_store(publication)
    else:
        fail_publication(publication, f"Unknown publication phase '{phase}'")

    return True
