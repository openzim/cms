#!/usr/bin/env python3
"""Maintenance script to normalize illustrations of books, titles and title histories"""

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm.attributes import flag_modified

from cms_backend import logger
from cms_backend.db import Session
from cms_backend.db.book import get_book
from cms_backend.db.models import Book, Title, TitleHistory
from cms_backend.db.title import get_title_by_id
from cms_backend.utils.zim import normalize_illustration


def normalize_book_illustrations(session: OrmSession):
    book_ids = session.scalars(select(Book.id)).all()
    nb_success = 0
    nb_failed = 0
    logger.info(f"Found {len(book_ids)} book(s) in database.")
    for book_id in book_ids:
        book = get_book(session, book_id=book_id)
        if book.zim_metadata.get("Illustration_48x48@1"):
            try:
                logger.debug(f"Normalizing illustration for book {book_id}")
                book.zim_metadata["Illustration_48x48@1"] = normalize_illustration(
                    book.zim_metadata["Illustration_48x48@1"]
                )
                flag_modified(book, "zim_metadata")
            except Exception as exc:
                logger.warning(
                    f"Unable to normalize illustration for book {book_id} illustration:"
                    f"\n{exc}"
                )
                nb_failed += 1
            else:
                session.add(book)
                nb_success += 1
        else:
            logger.warning(f"Book {book_id} has no illustration")

    if nb_success:
        session.commit()
    logger.info(f"Finished normalizing book illustrations: {nb_success=}, {nb_failed=}")


def normalize_title_illustrations(session: OrmSession):
    title_ids = session.scalars(
        select(Title.id).where(
            Title.illustration_48x48_at_1.is_not(None),
        )
    ).all()
    nb_success = 0
    nb_failed = 0
    logger.info(f"Found {len(title_ids)} titles(s) in database")
    for title_id in title_ids:
        title = get_title_by_id(session, title_id=title_id)
        try:
            logger.debug(f"Normalizing illustration for title {title_id}")
            title.illustration_48x48_at_1 = normalize_illustration(
                title.illustration_48x48_at_1  # pyright: ignore[reportArgumentType]
            )
        except Exception as exc:
            logger.warning(
                f"Unable to normalize illustration  for title {title_id} illustration: "
                f"\n{exc}"
            )
            nb_failed += 1
        else:
            session.add(title)
            nb_success += 1
    if nb_success:
        session.commit()
    logger.info(
        f"Finished normalizing title illustrations: {nb_success=}, {nb_failed=}"
    )


def normalize_title_history_illustrations(session: OrmSession):
    title_history_ids = session.scalars(
        select(TitleHistory.id).where(
            TitleHistory.illustration_48x48_at_1.is_not(None),
        )
    ).all()
    nb_success = 0
    nb_failed = 0
    logger.info(f"Found {len(title_history_ids)} title history in database")
    for title_history_id in title_history_ids:
        entry = session.scalars(
            select(TitleHistory).where(TitleHistory.id == title_history_id)
        ).one()
        try:
            logger.debug(
                f"Normalizing illustration for title history {title_history_id}"
            )
            entry.illustration_48x48_at_1 = normalize_illustration(
                entry.illustration_48x48_at_1  # pyright: ignore[reportArgumentType]
            )
        except Exception as exc:
            logger.warning(
                "Unable to normalize illustration for title history "
                f"{title_history_id} illustration: \n{exc}"
            )
            nb_failed += 1
        else:
            session.add(entry)
            nb_success += 1
    if nb_success:
        session.commit()
    logger.info(
        f"Finished normalizing illustrations for title history entries: {nb_success=}, "
        f"{nb_failed=}"
    )


def main():

    with Session() as session:
        normalize_book_illustrations(session)
        normalize_title_illustrations(session)
        normalize_title_history_illustrations(session)


if __name__ == "__main__":
    main()
