"""Add metadata fields to book table

Revision ID: add_book_metadata_fields
Revises: make_warehouse_paths_required
Create Date: 2025-11-10 00:00:01.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_book_metadata_fields"
down_revision = "make_warehouse_paths_required"
branch_labels = None
depends_on = None


def upgrade():
    # Add created_at field to book table (mandatory)
    op.add_column(
        "book",
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    # Add metadata fields to book table (optional)
    op.add_column(
        "book",
        sa.Column("name", sa.String(), nullable=True),
    )
    op.add_column(
        "book",
        sa.Column("date", sa.String(), nullable=True),
    )
    op.add_column(
        "book",
        sa.Column("flavour", sa.String(), nullable=True),
    )


def downgrade():
    # Drop metadata fields from book table
    op.drop_column("book", "flavour")
    op.drop_column("book", "date")
    op.drop_column("book", "name")
    op.drop_column("book", "created_at")
