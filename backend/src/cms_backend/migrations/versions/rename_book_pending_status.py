"""Rename book pending status to pending_processing

Revision ID: rename_book_pending
Revises: add_status_to_book
Create Date: 2025-11-03 01:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "rename_book_pending"
down_revision = "add_status_to_book"
branch_labels = None
depends_on = None


def upgrade():
    # Update existing books with status='pending' to status='pending_processing'
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE book SET status = 'pending_processing' WHERE status = 'pending'"
        )
    )

    # Update the default value for the status column
    op.alter_column(
        "book",
        "status",
        server_default="pending_processing",
        existing_type=sa.String(),
        existing_nullable=False,
    )

    # Create partial index for pending_processing status
    op.create_index(
        "idx_book_status_pending_processing",
        "book",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'pending_processing'"),
    )


def downgrade():
    # Drop the partial index
    op.drop_index(
        "idx_book_status_pending_processing",
        table_name="book",
    )

    # Restore the old default value
    op.alter_column(
        "book",
        "status",
        server_default="pending",
        existing_type=sa.String(),
        existing_nullable=False,
    )

    # Update existing books with status='pending_processing' back to status='pending'
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE book SET status = 'pending' WHERE status = 'pending_processing'"
        )
    )
