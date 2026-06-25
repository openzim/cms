import pathlib
import urllib.parse
from uuid import UUID

from kiwixstorage import (  # pyright: ignore[reportMissingTypeStubs]
    AuthenticationError,
    KiwixStorage,
)
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.models import Book
from cms_backend.shuttle.context import Context as ShuttleContext


def get_kiwix_storage_client(upload_uri: urllib.parse.ParseResult):
    def get_url_scheme(url: urllib.parse.ParseResult) -> str:
        if url.scheme.startswith("s3+http"):
            return "http"
        # covers both "s3" and "s3+https"
        elif url.scheme.startswith("s3") or url.scheme.startswith("s3+https"):
            return "https"
        else:
            raise ValueError(f"Unsupported URL scheme in: {url}")

    s3 = KiwixStorage(
        rebuild_uri(upload_uri, scheme=get_url_scheme(upload_uri)).geturl()
    )
    if not s3.check_credentials(  # pyright: ignore[reportUnknownMemberType]
        list_buckets=True, delete=True
    ):
        raise AuthenticationError("check_credentials failed")

    return s3


def delete_zimcheck_s3_results(session: OrmSession):
    """Delete zimcheck results from S3"""
    if not ShuttleContext.zimcheck_results_s3_bucket_uri:
        logger.warning(
            "Cannot delete zimcheck results from S3 because results upload uri is "
            "empty."
        )
        return
    try:
        upload_uri = urllib.parse.urlparse(
            ShuttleContext.zimcheck_results_s3_bucket_uri
        )
        pathlib.Path(upload_uri.path)
    except Exception as exc:
        raise ValueError(
            f"invalid upload URI: `{ShuttleContext.zimcheck_results_s3_bucket_uri}`"
        ) from exc

    s3 = get_kiwix_storage_client(upload_uri)

    logger.info("Deleting zimcheck results from S3")
    nb_deleted, nb_failed = 0, 0

    omit_book_ids: list[UUID] = []
    while True:
        books = session.scalars(
            select(Book)
            .where(
                Book.zimcheck_result_url.is_not(None),
                Book.zimcheck_s3_deleted.is_(False),
                Book.location_kind.in_(["prod", "deleted"]),
                Book.id.not_in(omit_book_ids),
            )
            .limit(50)
            .order_by(Book.created_at)
        ).all()

        if not books:
            logger.info(
                "No more books meet criteria for zimcheck results to be deleted."
            )
            break

        for book in books:
            omit_book_ids.append(book.id)
            try:
                s3.delete_object(
                    book.zimcheck_result_url.split("/")[-1],  # pyright: ignore[reportOptionalMemberAccess]
                )
            except Exception:
                logger.exception(
                    f"error while deleting zimcheck results for book {book.id}"
                )
                nb_failed += 1
            else:
                book.zimcheck_s3_deleted = True
                session.add(book)
                session.commit()
                nb_deleted += 1

    logger.info(f"Done deleting zimcheck files from S3: {nb_deleted=}, {nb_failed=}")


def rebuild_uri(uri: urllib.parse.ParseResult, scheme: str | None = None):
    netloc = ""
    scheme = scheme or uri.scheme
    if uri.username:
        netloc += uri.username
    if uri.password:
        netloc += f":{uri.password}"
    if uri.username or uri.password:
        netloc += "@"
    if uri.hostname:
        netloc += uri.hostname
    if uri.port:
        netloc += f":{uri.port}"
    return urllib.parse.urlparse(
        urllib.parse.urlunparse(
            [scheme, netloc, uri.path, uri.fragment, uri.query, uri.fragment]
        )
    )
