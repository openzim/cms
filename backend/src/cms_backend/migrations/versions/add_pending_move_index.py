"""Add partial index for pending_move book status

Revision ID: add_pending_move_index
Revises: add_book_location_table
Create Date: 2025-11-13 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_pending_move_index"
down_revision = "add_book_location_table"
branch_labels = None
depends_on = None


def upgrade():
    # Create partial index for pending_move status
    op.create_index(
        "idx_book_status_pending_move",
        "book",
        ["status"],
        postgresql_where="status = 'pending_move'",
    )


def downgrade():
    # Drop the partial index
    op.drop_index("idx_book_status_pending_move", table_name="book")
