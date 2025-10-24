from datetime import datetime
from ipaddress import IPv4Address
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    false,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)
from sqlalchemy.sql.schema import MetaData


class Base(MappedAsDataclass, DeclarativeBase):
    # This map details the specific transformation of types between Python and
    # PostgreSQL. This is only needed for the case where a specific PostgreSQL
    # type has to be used or when we want to ensure a specific setting (like the
    # timezone below)
    type_annotation_map = {  # noqa: RUF012
        dict[str, Any]: MutableDict.as_mutable(
            JSONB
        ),  # transform Python Dict[str, Any] into PostgreSQL JSONB
        list[dict[str, Any]]: MutableList.as_mutable(JSONB),
        list[tuple[str, Any]]: MutableList.as_mutable(JSONB),
        datetime: DateTime(
            timezone=False
        ),  # transform Python datetime into PostgreSQL Datetime without timezone
        list[str]: ARRAY(
            item_type=String
        ),  # transform Python List[str] into PostgreSQL Array of strings
        IPv4Address: INET,  # transform Python IPV4Address into PostgreSQL INET
    }

    # This metadata specifies some naming conventions that will be used by
    # alembic to generate constraints names (indexes, unique constraints, ...)
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
    pass


class ZimfarmNotification(Base):
    __tablename__ = "zimfarm_notification"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    received_at: Mapped[datetime]
    content: Mapped[dict[str, Any]]
    processed: Mapped[bool] = mapped_column(default=False, server_default=false())
    errored: Mapped[bool] = mapped_column(default=False, server_default=false())
    events: Mapped[list[str]] = mapped_column(init=False, default_factory=list)

    book_id: Mapped[UUID | None] = mapped_column(ForeignKey("book.id"), init=False)
    book: Mapped[Optional["Book"]] = relationship(
        init=False, back_populates="zimfarm_notification"
    )


Index(
    "idx_zimfarm_notification_processed_false",
    ZimfarmNotification.processed,
    postgresql_where=ZimfarmNotification.processed.is_(False),
)

Index(
    "idx_zimfarm_notification_errored_false",
    ZimfarmNotification.errored,
    postgresql_where=ZimfarmNotification.errored.is_(True),
)


class Book(Base):
    __tablename__ = "book"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    article_count: Mapped[int]
    media_count: Mapped[int]
    size: Mapped[int]
    zimcheck_result: Mapped[dict[str, Any]]
    zim_metadata: Mapped[dict[str, Any]]
    events: Mapped[list[str]] = mapped_column(init=False, default_factory=list)

    title_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("title.id", use_alter=True), init=False
    )
    title: Mapped[Optional["Title"]] = relationship(init=False, foreign_keys=[title_id])

    zimfarm_notification: Mapped[Optional["ZimfarmNotification"]] = relationship(
        back_populates="book"
    )


class Title(Base):
    __tablename__ = "title"
    id: Mapped[UUID] = mapped_column(
        init=False, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    name: Mapped[str]
    events: Mapped[list[str]] = mapped_column(init=False, default_factory=list)
    books: Mapped[list["Book"]] = relationship(
        back_populates="title",
        cascade="save-update, merge, refresh-expire",
        init=False,
        foreign_keys=[Book.title_id],
    )
