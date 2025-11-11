"""Add warehouse paths and in_prod to title

Revision ID: add_warehouse_paths_to_title
Revises: add_warehouse_tables
Create Date: 2025-11-07 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "add_warehouse_paths_to_title"
down_revision = "add_warehouse_tables"
branch_labels = None
depends_on = None


def upgrade():
    # Add warehouse path references and in_prod flag to title table
    op.add_column(
        "title",
        sa.Column("dev_warehouse_path_id", UUID(), nullable=True),
    )
    op.add_column(
        "title",
        sa.Column("prod_warehouse_path_id", UUID(), nullable=True),
    )
    op.add_column(
        "title",
        sa.Column(
            "in_prod",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # Add foreign key constraints
    op.create_foreign_key(
        "fk_title_dev_warehouse_path_id_warehouse_path",
        "title",
        "warehouse_path",
        ["dev_warehouse_path_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_title_prod_warehouse_path_id_warehouse_path",
        "title",
        "warehouse_path",
        ["prod_warehouse_path_id"],
        ["id"],
    )


def downgrade():
    # Drop foreign key constraints first
    op.drop_constraint(
        "fk_title_prod_warehouse_path_id_warehouse_path", "title", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_title_dev_warehouse_path_id_warehouse_path", "title", type_="foreignkey"
    )

    # Drop columns
    op.drop_column("title", "in_prod")
    op.drop_column("title", "prod_warehouse_path_id")
    op.drop_column("title", "dev_warehouse_path_id")
