"""Add producer fields to book and title

Revision ID: add_producer_fields
Revises: add_warehouse_paths_to_title
Create Date: 2025-11-07 00:00:01.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_producer_fields"
down_revision = "add_warehouse_paths_to_title"
branch_labels = None
depends_on = None


def upgrade():
    # Add producer fields to book table (mandatory)
    op.add_column(
        "book",
        sa.Column("producer_display_name", sa.String(), nullable=False),
    )
    op.add_column(
        "book",
        sa.Column("producer_display_url", sa.String(), nullable=False),
    )
    op.add_column(
        "book",
        sa.Column("producer_unique_id", sa.String(), nullable=False),
    )

    # Add producer fields to title table (mandatory)
    op.add_column(
        "title",
        sa.Column("producer_display_name", sa.String(), nullable=False),
    )
    op.add_column(
        "title",
        sa.Column("producer_display_url", sa.String(), nullable=False),
    )
    op.add_column(
        "title",
        sa.Column("producer_unique_id", sa.String(), nullable=False),
    )


def downgrade():
    # Drop producer fields from title table
    op.drop_column("title", "producer_unique_id")
    op.drop_column("title", "producer_display_url")
    op.drop_column("title", "producer_display_name")

    # Drop producer fields from book table
    op.drop_column("book", "producer_unique_id")
    op.drop_column("book", "producer_display_url")
    op.drop_column("book", "producer_display_name")
