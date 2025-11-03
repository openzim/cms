"""Add status column to book

Revision ID: add_status_to_book
Revises: add_status_to_notif
Create Date: 2025-11-03 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_status_to_book"
down_revision = "add_status_to_notif"
branch_labels = None
depends_on = None


def upgrade():
    # Add status column with default value 'pending'
    op.add_column(
        "book",
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
    )

    # For existing books, set status based on title_id
    # - If book has title_id, it was processed successfully -> "processed"
    # - If book has no title_id, it's pending a title -> "pending_title"
    conn = op.get_bind()

    # Set status to "processed" where title_id is not null
    conn.execute(
        sa.text("UPDATE book SET status = 'processed' WHERE title_id IS NOT NULL")
    )

    # Set status to "pending_title" where title_id is null
    conn.execute(
        sa.text("UPDATE book SET status = 'pending_title' WHERE title_id IS NULL")
    )

    # Create partial indexes for specific status values
    # These indexes help efficiently query for books that need attention
    op.create_index(
        "idx_book_status_qa_failed",
        "book",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'qa_failed'"),
    )

    op.create_index(
        "idx_book_status_pending_title",
        "book",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'pending_title'"),
    )

    op.create_index(
        "idx_book_status_errored",
        "book",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'errored'"),
    )


def downgrade():
    # Drop the partial indexes
    op.drop_index("idx_book_status_errored", table_name="book")
    op.drop_index("idx_book_status_pending_title", table_name="book")
    op.drop_index("idx_book_status_qa_failed", table_name="book")

    # Drop status column
    op.drop_column("book", "status")
