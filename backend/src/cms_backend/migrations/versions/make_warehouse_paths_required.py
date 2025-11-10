"""Make warehouse paths required on title

Revision ID: make_warehouse_paths_required
Revises: 92d03596d8f7
Create Date: 2025-11-10 00:00:00.000000

"""

from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "make_warehouse_paths_required"
down_revision = "92d03596d8f7"
branch_labels = None
depends_on = None


def upgrade():
    # Make warehouse path columns non-nullable
    op.alter_column(
        "title",
        "dev_warehouse_path_id",
        existing_type=UUID(),
        nullable=False,
    )
    op.alter_column(
        "title",
        "prod_warehouse_path_id",
        existing_type=UUID(),
        nullable=False,
    )


def downgrade():
    # Revert warehouse path columns to nullable
    op.alter_column(
        "title",
        "prod_warehouse_path_id",
        existing_type=UUID(),
        nullable=True,
    )
    op.alter_column(
        "title",
        "dev_warehouse_path_id",
        existing_type=UUID(),
        nullable=True,
    )
