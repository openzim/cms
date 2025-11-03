"""Add warehouse and warehouse_path tables

Revision ID: add_warehouse_tables
Revises: rename_book_pending
Create Date: 2025-11-03 02:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = "add_warehouse_tables"
down_revision = "rename_book_pending"
branch_labels = None
depends_on = None


def upgrade():
    # Create warehouse table
    op.create_table(
        "warehouse",
        sa.Column(
            "id", UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("configuration", JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_warehouse"),
    )

    # Create warehouse_path table
    op.create_table(
        "warehouse_path",
        sa.Column(
            "id", UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False
        ),
        sa.Column("folder_name", sa.String(), nullable=False),
        sa.Column("warehouse_id", UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouse.id"],
            name="fk_warehouse_path_warehouse_id_warehouse",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_warehouse_path"),
    )


def downgrade():
    # Drop tables in reverse order due to foreign key constraint
    op.drop_table("warehouse_path")
    op.drop_table("warehouse")
