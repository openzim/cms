"""Add book_location table to store current and target file locations

Revision ID: add_book_location_table
Revises: title_warehouse_paths
Create Date: 2025-11-11 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "add_book_location_table"
down_revision = "title_warehouse_paths"
branch_labels = None
depends_on = None


def upgrade():
    # Create the book_location table with composite primary key
    op.create_table(
        "book_location",
        sa.Column("book_id", UUID(), nullable=False),
        sa.Column("warehouse_path_id", UUID(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["book_id"], ["book.id"], name="fk_book_location_book_id_book"
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_path_id"],
            ["warehouse_path.id"],
            name="fk_book_location_warehouse_path_id_warehouse_path",
        ),
        sa.PrimaryKeyConstraint(
            "book_id", "warehouse_path_id", "status", name="pk_book_location"
        ),
    )


def downgrade():
    op.drop_table("book_location")
