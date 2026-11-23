"""move illustrations to a dedicated table

Revision ID: d1e2f3a4b5c6
Revises: 60d208b4fe0a
Create Date: 2026-11-20

"""

import base64
from copy import deepcopy
from typing import Any

import sqlalchemy as sa
import xxhash
from alembic import op

# revision identifiers, used by Alembic.
revision = "d1e2f3a4b5c6"
down_revision = "60d208b4fe0a"
branch_labels = None
depends_on = None

ILLUSTRATION_METADATA_PREFIX = "Illustration"
HEX_DIGEST_SUFFIX = "_hex_digest"


def _store_illustration(
    connection: sa.Connection,
    illustration_table: Any,
    stored: set[str],
    value: Any,
) -> str | None:
    if value in (None, ""):
        return None

    value = str(value)
    data = base64.b64decode(value, validate=True)
    hex_digest = xxhash.xxh3_64_hexdigest(data)
    if hex_digest not in stored:
        connection.execute(
            illustration_table.insert().values(hex_digest=hex_digest, data=value)
        )
        stored.add(hex_digest)
    return hex_digest


def _migrate_title_table(
    connection: sa.Connection,
    illustration_table: Any,
    stored: set[str],
    table_name: str,
) -> None:
    rows = connection.execute(
        sa.text(
            f"SELECT id, illustration_48x48_at_1_hex_digest "  # noqa: S608
            f"FROM {table_name}"
        )
    ).all()
    for row_id, value in rows:
        try:
            hex_digest = _store_illustration(
                connection, illustration_table, stored, value
            )
        except ValueError as exc:
            raise ValueError(
                f"{table_name} {row_id} has an invalid base64 illustration"
            ) from exc

        if hex_digest == value:
            continue

        connection.execute(
            sa.text(
                f"UPDATE {table_name} "  # noqa: S608
                f"SET illustration_48x48_at_1_hex_digest = :hex_digest "
                "WHERE id = :id"
            ),
            {"hex_digest": hex_digest, "id": row_id},
        )


def _migrate_book_metadata(
    connection: sa.Connection, illustration_table: Any, stored: set[str]
) -> None:
    book_table = sa.Table("book", sa.MetaData(), autoload_with=connection)
    for book_id, zim_metadata in connection.execute(
        sa.select(book_table.c.id, book_table.c.zim_metadata)
    ).all():
        if not zim_metadata:
            continue

        updated_metadata = deepcopy(zim_metadata)
        for key in list(updated_metadata):
            if not key.startswith(ILLUSTRATION_METADATA_PREFIX):
                continue
            if key.endswith(HEX_DIGEST_SUFFIX):
                continue

            value = updated_metadata.pop(key)
            try:
                hex_digest = _store_illustration(
                    connection, illustration_table, stored, value
                )
            except ValueError as exc:
                raise ValueError(
                    f"Book {book_id} has an invalid base64 illustration"
                ) from exc

            if hex_digest is not None:
                updated_metadata[f"{key}{HEX_DIGEST_SUFFIX}"] = hex_digest

        if updated_metadata == zim_metadata:
            continue

        connection.execute(
            book_table.update()
            .where(book_table.c.id == book_id)
            .values(zim_metadata=updated_metadata)
        )


def upgrade() -> None:
    connection = op.get_bind()

    op.create_table(
        "illustration",
        sa.Column("hex_digest", sa.String(), nullable=False),
        sa.Column("data", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("hex_digest", name=op.f("pk_illustration")),
    )

    op.alter_column(
        "title",
        "illustration_48x48_at_1",
        new_column_name="illustration_48x48_at_1_hex_digest",
    )

    op.alter_column(
        "title_history",
        "illustration_48x48_at_1",
        new_column_name="illustration_48x48_at_1_hex_digest",
    )

    illustration_table = sa.table(
        "illustration",
        sa.column("hex_digest", sa.String()),
        sa.column("data", sa.String()),
    )
    stored: set[str] = set()

    _migrate_title_table(connection, illustration_table, stored, "title")
    _migrate_title_table(connection, illustration_table, stored, "title_history")
    _migrate_book_metadata(connection, illustration_table, stored)

    op.create_foreign_key(
        op.f("fk_title_illustration_48x48_at_1_hex_digest_illustration"),
        "title",
        "illustration",
        ["illustration_48x48_at_1_hex_digest"],
        ["hex_digest"],
    )
    op.create_foreign_key(
        op.f("fk_title_history_illustration_48x48_at_1_hex_digest_illustration"),
        "title_history",
        "illustration",
        ["illustration_48x48_at_1_hex_digest"],
        ["hex_digest"],
    )


def _restore_title_table(
    connection: sa.Connection, encoded: dict[str, str], table_name: str
) -> None:
    rows = connection.execute(
        sa.text(
            f"SELECT id, illustration_48x48_at_1_hex_digest "  # noqa: S608
            f"FROM {table_name}"
        )
    ).all()
    for row_id, value in rows:
        raw_value = encoded.get(value) if value is not None else None
        connection.execute(
            sa.text(
                f"UPDATE {table_name} "  # noqa: S608
                f"SET illustration_48x48_at_1_hex_digest = :value "
                "WHERE id = :id"
            ),
            {"value": raw_value, "id": row_id},
        )


def _restore_book_metadata(connection: sa.Connection, encoded: dict[str, str]) -> None:
    book_table = sa.Table("book", sa.MetaData(), autoload_with=connection)
    for book_id, zim_metadata in connection.execute(
        sa.select(book_table.c.id, book_table.c.zim_metadata)
    ).all():
        if not zim_metadata:
            continue

        updated_metadata = deepcopy(zim_metadata)
        for key in list(updated_metadata):
            if not key.endswith(HEX_DIGEST_SUFFIX):
                continue

            illustration_key = key.removesuffix(HEX_DIGEST_SUFFIX)
            if not illustration_key.startswith(ILLUSTRATION_METADATA_PREFIX):
                continue

            hex_digest = updated_metadata.pop(key)
            updated_metadata[illustration_key] = encoded.get(hex_digest)

        if updated_metadata == zim_metadata:
            continue

        connection.execute(
            book_table.update()
            .where(book_table.c.id == book_id)
            .values(zim_metadata=updated_metadata)
        )


def downgrade() -> None:
    connection = op.get_bind()

    op.drop_constraint(
        op.f("fk_title_history_illustration_48x48_at_1_hex_digest_illustration"),
        "title_history",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_title_illustration_48x48_at_1_hex_digest_illustration"),
        "title",
        type_="foreignkey",
    )

    illustration_table = sa.Table(
        "illustration", sa.MetaData(), autoload_with=connection
    )
    encoded: dict[str, str] = dict(
        connection.execute(
            sa.select(illustration_table.c.hex_digest, illustration_table.c.data)
        ).all()
    )

    _restore_title_table(connection, encoded, "title")
    _restore_title_table(connection, encoded, "title_history")
    _restore_book_metadata(connection, encoded)

    op.alter_column(
        "title",
        "illustration_48x48_at_1_hex_digest",
        new_column_name="illustration_48x48_at_1",
    )

    op.alter_column(
        "title_history",
        "illustration_48x48_at_1_hex_digest",
        new_column_name="illustration_48x48_at_1",
    )

    op.drop_table("illustration")
