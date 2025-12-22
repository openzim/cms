"""refactor book status to flags

Revision ID: 6376af219731
Revises: 5376af219730
Create Date: 2025-12-22 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "6376af219731"
down_revision = "5376af219730"
branch_labels = None
depends_on = None


def upgrade():
    # Add new boolean columns (nullable initially)
    op.add_column(
        "book",
        sa.Column("needs_processing", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "book",
        sa.Column("has_error", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "book",
        sa.Column("needs_file_operation", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "book",
        sa.Column("location_kind", sa.String(), nullable=True),
    )

    # Migrate data from status to boolean flags
    op.execute(
        text(
            """
        UPDATE book SET
            needs_processing = CASE
                WHEN status = 'pending_processing' THEN TRUE
                ELSE FALSE
            END,
            has_error = CASE
                WHEN status IN ('bad_book', 'errored') THEN TRUE
                ELSE FALSE
            END,
            needs_file_operation = CASE
                WHEN status = 'pending_move' THEN TRUE
                ELSE FALSE
            END
        """
        )
    )

    # Set initial location_kind based on current BookLocation warehouse_id
    # This requires joining with BookLocation to find current locations
    op.execute(
        text(
            """
        UPDATE book SET location_kind = 'jail'
        WHERE location_kind IS NULL
        """
        )
    )

    # Make boolean columns non-nullable with defaults
    op.alter_column(
        "book",
        "needs_processing",
        nullable=False,
        server_default="false",
        existing_type=sa.Boolean(),
    )
    op.alter_column(
        "book",
        "has_error",
        nullable=False,
        server_default="false",
        existing_type=sa.Boolean(),
    )
    op.alter_column(
        "book",
        "needs_file_operation",
        nullable=False,
        server_default="false",
        existing_type=sa.Boolean(),
    )
    op.alter_column(
        "book",
        "location_kind",
        nullable=False,
        server_default="jail",
        existing_type=sa.String(),
    )

    # Drop old conditional indexes on status column
    op.drop_index(
        "idx_book_status_pending_processing",
        table_name="book",
        postgresql_where=sa.text("status = 'pending_processing'"),
    )
    op.drop_index(
        "idx_book_status_bad_book",
        table_name="book",
        postgresql_where=sa.text("status = 'bad_book'"),
    )
    op.drop_index(
        "idx_book_status_pending_title",
        table_name="book",
        postgresql_where=sa.text("status = 'pending_title'"),
    )
    op.drop_index(
        "idx_book_status_errored",
        table_name="book",
        postgresql_where=sa.text("status = 'errored'"),
    )
    op.drop_index(
        "idx_book_status_pending_move",
        table_name="book",
        postgresql_where=sa.text("status = 'pending_move'"),
    )

    # Create new conditional indexes for boolean flags
    op.create_index(
        "idx_book_needs_processing",
        "book",
        ["needs_processing"],
        unique=False,
        postgresql_where=sa.text("needs_processing = TRUE"),
    )
    op.create_index(
        "idx_book_has_error",
        "book",
        ["has_error"],
        unique=False,
        postgresql_where=sa.text("has_error = TRUE"),
    )
    op.create_index(
        "idx_book_needs_file_operation",
        "book",
        ["needs_file_operation"],
        unique=False,
        postgresql_where=sa.text("needs_file_operation = TRUE"),
    )

    # Create partial indexes for location_kind (only jail and staging, not prod)
    op.create_index(
        "idx_book_location_kind_jail",
        "book",
        ["location_kind"],
        unique=False,
        postgresql_where=sa.text("location_kind = 'jail'"),
    )
    op.create_index(
        "idx_book_location_kind_staging",
        "book",
        ["location_kind"],
        unique=False,
        postgresql_where=sa.text("location_kind = 'staging'"),
    )

    # Drop old status column
    op.drop_column("book", "status")


def downgrade():
    # Re-add status column
    op.add_column(
        "book",
        sa.Column(
            "status",
            sa.String(),
            server_default="pending_processing",
            nullable=False,
        ),
    )

    # Migrate data from boolean flags back to status
    op.execute(
        text(
            """
        UPDATE book SET status = CASE
            WHEN has_error = TRUE AND needs_processing = FALSE THEN 'errored'
            WHEN has_error = TRUE THEN 'bad_book'
            WHEN needs_file_operation = TRUE THEN 'pending_move'
            WHEN needs_processing = TRUE THEN 'pending_processing'
            ELSE 'published'
        END
        """
        )
    )

    # Drop new indexes
    op.drop_index("idx_book_location_kind_staging", table_name="book")
    op.drop_index("idx_book_location_kind_jail", table_name="book")
    op.drop_index(
        "idx_book_needs_file_operation",
        table_name="book",
        postgresql_where=sa.text("needs_file_operation = TRUE"),
    )
    op.drop_index(
        "idx_book_has_error",
        table_name="book",
        postgresql_where=sa.text("has_error = TRUE"),
    )
    op.drop_index(
        "idx_book_needs_processing",
        table_name="book",
        postgresql_where=sa.text("needs_processing = TRUE"),
    )

    # Re-create old conditional indexes
    op.create_index(
        "idx_book_status_pending_move",
        "book",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'pending_move'"),
    )
    op.create_index(
        "idx_book_status_errored",
        "book",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'errored'"),
    )
    op.create_index(
        "idx_book_status_pending_title",
        "book",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'pending_title'"),
    )
    op.create_index(
        "idx_book_status_bad_book",
        "book",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'bad_book'"),
    )
    op.create_index(
        "idx_book_status_pending_processing",
        "book",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'pending_processing'"),
    )

    # Drop new boolean columns
    op.drop_column("book", "location_kind")
    op.drop_column("book", "needs_file_operation")
    op.drop_column("book", "has_error")
    op.drop_column("book", "needs_processing")
