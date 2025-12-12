"""Add library and library_warehouse_path tables

Revision ID: add_library_tables
Revises: add_pending_move_index
Create Date: 2025-11-18 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "add_library_tables"
down_revision = "add_pending_move_index"
branch_labels = None
depends_on = None


def upgrade():
    # Create library table
    op.create_table(
        "library",
        sa.Column(
            "id", UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_library"),
        sa.UniqueConstraint("name", name="uq_library_name"),
    )

    # Create unique index on library name for fast lookups
    op.create_index("ix_library_name", "library", ["name"], unique=True)

    # Create library_warehouse_path junction table
    op.create_table(
        "library_warehouse_path",
        sa.Column("library_id", UUID(), nullable=False),
        sa.Column("warehouse_path_id", UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["library_id"],
            ["library.id"],
            name="fk_library_warehouse_path_library_id_library",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_path_id"],
            ["warehouse_path.id"],
            name="fk_library_warehouse_path_warehouse_path_id_warehouse_path",
        ),
        sa.PrimaryKeyConstraint(
            "library_id", "warehouse_path_id", name="pk_library_warehouse_path"
        ),
    )


def downgrade():
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table("library_warehouse_path")
    op.drop_table("library")
