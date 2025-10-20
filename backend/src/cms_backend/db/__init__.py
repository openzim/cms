from collections.abc import Callable, Generator
from typing import Any

from bson.json_util import RELAXED_JSON_OPTIONS, dumps, loads
from sqlalchemy import SelectBase, create_engine, func, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker

from cms_backend.context import Context


# custom overload of bson deserializer to make naive datetime
# this is needed to have objects from the DB with naive datetime properties
# (otherwise the deserialization produces aware datetimes based on local TZ)
def cms_loads(s: str, *args: Any, **kwargs: Any) -> Any:
    return loads(
        s,
        *args,
        json_options=RELAXED_JSON_OPTIONS.with_options(tz_aware=False, tzinfo=None),
        **kwargs,
    )


# custom overload of bson serializer to convert datetime objects to milliseconds
# and clarify which format is used
def cms_dumps(obj: Any, *args: Any, **kwargs: Any):
    return dumps(obj, *args, json_options=RELAXED_JSON_OPTIONS, **kwargs)


if (
    Context.database_url == "nodb"
):  # this is a hack for cases where we do not need the DB, e.g. unit tests
    Session = None
else:
    Session = sessionmaker(
        bind=create_engine(
            Context.database_url,
            echo=False,
            json_serializer=cms_dumps,
            json_deserializer=cms_loads,
        )
    )


def gen_dbsession() -> Generator[OrmSession]:
    """FastAPI's Depends() compatible helper to provide a DB transaction.

    Commit is automatically performed and transactions are rolled back in
    the event of exceptions
    """
    if Session is None:
        raise RuntimeError("DB is disabled")

    with Session.begin() as session:
        yield session


def gen_manual_dbsession() -> Generator[OrmSession]:
    """FastAPI's Depends() compatible helper to provide a DB Session.

    Transaction must be managed by the developer (e.g perform  a commit/rollback)
    """
    if Session is None:
        raise RuntimeError("DB is disabled")

    with Session() as session:
        yield session


def dbsession(
    func: Callable[..., Any],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to create an SQLAlchemy ORM session object and wrap the function
    inside the session. A `session` argument is automatically set. Commit is
    automatically performed when the function finish (and before returning to
    the caller). Should any exception arise, rollback of the transaction is also
    automatic.
    """

    def inner(*args: Any, **kwargs: Any) -> Any:
        if Session is None:
            raise RuntimeError("DB is disabled")

        with Session.begin() as session:
            kwargs["session"] = session
            return func(*args, **kwargs)

    return inner


def dbsession_manual(
    func: Callable[..., Any],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to create an SQLAlchemy ORM session object and wrap the function
    inside the session. A `session` argument is automatically set. Transaction must
    be managed by the developer (e.g. perform a commit / rollback).
    """

    def inner(*args: Any, **kwargs: Any) -> Any:
        if Session is None:
            raise RuntimeError("DB is disabled")

        with Session() as session:
            kwargs["session"] = session
            return func(*args, **kwargs)

    return inner


def count_from_stmt(session: OrmSession, stmt: SelectBase) -> int:
    """Count all records returned by any statement `stmt` passed as parameter"""
    return session.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()
