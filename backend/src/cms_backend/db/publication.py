from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import ApplicationPublication
from cms_backend.schemas.models import ApplicationPublicationCreateSchema
from cms_backend.schemas.orms import ApplicationPublicationSchema, ListResult
from cms_backend.utils.github import get_tag_prefix, github_client

TERMINAL_STATUSES = {"success", "failure", "cancelled"}


def create_publication(
    session: OrmSession,
    *,
    payload: ApplicationPublicationCreateSchema,
) -> ApplicationPublication:
    publication = ApplicationPublication(
        title_id=payload.title_id,
        flavour=payload.flavour,
        store=payload.store,
        content_version=payload.content_version,
        tag=payload.tag,
        commit_sha=payload.commit_sha,
        repository=payload.repository,
        workflow=payload.workflow,
        release_id=payload.release_id,
        release_url=payload.release_url,
        requested_by_id=payload.requested_by_id,
        status="pending",
    )
    session.add(publication)
    session.flush()
    return publication


def get_publication_or_none(
    session: OrmSession, *, publication_id: UUID
) -> ApplicationPublication | None:
    return session.scalars(
        select(ApplicationPublication)
        .where(
            ApplicationPublication.id == publication_id,
        )
        .options(selectinload(ApplicationPublication.requested_by))
    ).one_or_none()


def get_publication(
    session: OrmSession, *, publication_id: UUID
) -> ApplicationPublication:
    publication = get_publication_or_none(session, publication_id=publication_id)
    if publication is None:
        raise RecordDoesNotExistError(f"Publication {publication_id} does not exist")
    return publication


def has_successful_publication(
    session: OrmSession,
    *,
    title_id: UUID,
    flavour: str,
    store: str,
    app_name: str,
    content_version: str,
) -> bool:
    """Whether this app already published this content version successfully."""
    base_tag = get_tag_prefix(app_name=app_name, content_version=content_version)
    stmt = (
        select(ApplicationPublication.id)
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
        .limit(1)
    )
    return session.scalar(stmt) is not None


def get_publications(
    session: OrmSession,
    *,
    title_id: UUID | None = None,
    flavour: str | None = None,
    store: str | None = None,
    skip: int = 0,
    limit: int = 20,
    refresh: bool = False,
) -> ListResult[ApplicationPublicationSchema]:
    stmt = (
        select(ApplicationPublication)
        .where(
            (ApplicationPublication.title_id == title_id) | (title_id is None),
            (ApplicationPublication.flavour == flavour) | (flavour is None),
            (ApplicationPublication.store == store) | (store is None),
        )
        .options(selectinload(ApplicationPublication.requested_by))
    )
    records = session.scalars(
        stmt.order_by(ApplicationPublication.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    if refresh:
        for publication in records:
            refresh_publication(session, publication)

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
        status=publication.status,
        content_version=publication.content_version,
        tag=publication.tag,
        release_url=publication.release_url,
        run_url=publication.run_url,
        error=publication.error,
        requested_by=(
            publication.requested_by.username if publication.requested_by else None
        ),
        created_at=publication.created_at,
        updated_at=publication.updated_at,
    )


def refresh_publication(
    session: OrmSession, publication: ApplicationPublication
) -> ApplicationPublication:
    """Update the publication status from the matching GitHub Actions run."""
    if publication.status in TERMINAL_STATUSES:
        return publication

    run: dict[str, Any] | None = None
    if publication.run_id is not None:
        run = github_client.get_workflow_run(
            repo=publication.repository, run_id=publication.run_id
        )
    if run is None:
        run = github_client.get_run_for_publication(
            repo=publication.repository,
            workflow=publication.workflow,
            tag=publication.tag,
            commit_sha=publication.commit_sha,
        )
        if run is not None:
            publication.run_id = run.get("id")
            publication.run_url = run.get("html_url")

    if run is None:
        return publication

    run_status = run.get("status")
    conclusion = run.get("conclusion")
    if run_status == "completed":
        if conclusion == "success":
            publication.status = "success"
        elif conclusion == "cancelled":
            publication.status = "cancelled"
        else:
            publication.status = "failure"
            publication.error = str(conclusion or "workflow failed")
    elif run_status in {"queued", "in_progress", "waiting", "pending", "requested"}:
        publication.status = "running"

    session.flush()
    return publication
