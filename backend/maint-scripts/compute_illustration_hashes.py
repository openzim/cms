#!/usr/bin/env python3
"""Maintenance script to compute illustration hashes of books and titles whose
illustration hashes are missing
"""

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db import Session
from cms_backend.db.book import get_book
from cms_backend.db.models import Book, Title, TitleHistory
from cms_backend.db.title import get_title_by_id
from cms_backend.utils.zim import compute_illustration_hash


def compute_book_hashes(session: OrmSession):
    book_ids = session.scalars(
        select(Book.id).where(Book.illustration_48x48_at_1_hash.is_(None))
    ).all()
    nb_computed = 0
    nb_failed = 0
    logger.info(f"Found {len(book_ids)} book(s) with no illustration hashes.")
    for book_id in book_ids:
        book = get_book(session, book_id=book_id)
        if book.zim_metadata.get("Illustration_48x48@1"):
            try:
                logger.debug(f"Computing illustration hash for book {book_id}")
                book.illustration_48x48_at_1_hash = compute_illustration_hash(
                    book.zim_metadata["Illustration_48x48@1"]
                )
            except Exception as exc:
                logger.warning(
                    f"Unable to compute hash for book {book_id} illustration: \n{exc}"
                )
                nb_failed += 1
            else:
                session.add(book)
                nb_computed += 1
        else:
            logger.warning(f"Book {book_id} has no illustration")

    if nb_computed:
        session.commit()
    logger.info(
        f"Finished computing book illustration hashes: {nb_computed=}, {nb_failed=}"
    )


def compute_title_hashes(session: OrmSession):
    title_ids = session.scalars(
        select(Title.id).where(
            Title.illustration_48x48_at_1.is_not(None),
            Title.illustration_48x48_at_1_hash.is_(None),
        )
    ).all()
    nb_computed = 0
    nb_failed = 0
    logger.info(f"Found {len(title_ids)} titles(s) with no illustration hashes.")
    for title_id in title_ids:
        title = get_title_by_id(session, title_id=title_id)
        try:
            logger.debug(f"Computing illustration hash for title {title_id}")
            title.illustration_48x48_at_1_hash = compute_illustration_hash(
                title.illustration_48x48_at_1  # pyright: ignore[reportArgumentType]
            )
        except Exception as exc:
            logger.warning(
                f"Unable to compute hash for title {title_id} illustration: \n{exc}"
            )
            nb_failed += 1
        else:
            session.add(title)
            nb_computed += 1
    if nb_computed:
        session.commit()
    logger.info(
        f"Finished computing title illustration hashes: {nb_computed=}, {nb_failed=}"
    )


def compute_title_history_hashes(session: OrmSession):
    title_history_ids = session.scalars(
        select(TitleHistory.id).where(
            TitleHistory.illustration_48x48_at_1.is_not(None),
            TitleHistory.illustration_48x48_at_1_hash.is_(None),
        )
    ).all()
    nb_computed = 0
    nb_failed = 0
    logger.info(
        f"Found {len(title_history_ids)} title history with no illustration hashes."
    )
    for title_history_id in title_history_ids:
        entry = session.scalars(
            select(TitleHistory).where(TitleHistory.id == title_history_id)
        ).one()
        try:
            logger.debug(
                f"Computing illustration hash for title history {title_history_id}"
            )
            entry.illustration_48x48_at_1_hash = compute_illustration_hash(
                entry.illustration_48x48_at_1  # pyright: ignore[reportArgumentType]
            )
        except Exception as exc:
            logger.warning(
                f"Unable to compute hash for title history {title_history_id} "
                f"illustration: \n{exc}"
            )
            nb_failed += 1
        else:
            session.add(entry)
            nb_computed += 1
    if nb_computed:
        session.commit()
    logger.info(
        f"Finished computing title history illustration hashes: {nb_computed=}, "
        f"{nb_failed=}"
    )


def main():

    with Session() as session:
        compute_book_hashes(session)
        compute_title_hashes(session)
        compute_title_history_hashes(session)


if __name__ == "__main__":
    main()
