"""Add title_warehouse_path junction table to support multiple warehouse paths

Revision ID: title_warehouse_paths
Revises: add_book_metadata_fields
Create Date: 2025-11-11 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "title_warehouse_paths"
down_revision = "add_book_metadata_fields"
branch_labels = None
depends_on = None


def upgrade():
    # Create the junction table with composite primary key
    op.create_table(
        "title_warehouse_path",
        sa.Column("title_id", UUID(), nullable=False),
        sa.Column("warehouse_path_id", UUID(), nullable=False),
        sa.Column("path_type", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["title_id"], ["title.id"], name="fk_title_warehouse_path_title_id_title"
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_path_id"],
            ["warehouse_path.id"],
            name="fk_title_warehouse_path_warehouse_path_id_warehouse_path",
        ),
        sa.PrimaryKeyConstraint(
            "title_id", "warehouse_path_id", "path_type", name="pk_title_warehouse_path"
        ),
    )

    # Migrate data from old columns to junction table
    op.execute(
        """
        INSERT INTO title_warehouse_path (title_id, warehouse_path_id, path_type)
        SELECT id, dev_warehouse_path_id, 'dev' FROM title
        WHERE dev_warehouse_path_id IS NOT NULL
    """
    )

    op.execute(
        """
        INSERT INTO title_warehouse_path (title_id, warehouse_path_id, path_type)
        SELECT id, prod_warehouse_path_id, 'prod' FROM title
        WHERE prod_warehouse_path_id IS NOT NULL
    """
    )

    # Drop the old columns and foreign keys
    op.drop_constraint(
        "fk_title_prod_warehouse_path_id_warehouse_path", "title", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_title_dev_warehouse_path_id_warehouse_path", "title", type_="foreignkey"
    )

    op.drop_column("title", "dev_warehouse_path_id")
    op.drop_column("title", "prod_warehouse_path_id")


def downgrade():
    # Add back the old columns
    op.add_column(
        "title",
        sa.Column("dev_warehouse_path_id", UUID(), nullable=True),
    )
    op.add_column(
        "title",
        sa.Column("prod_warehouse_path_id", UUID(), nullable=True),
    )

    # Migrate data back from junction table to old columns
    op.execute(
        """
        UPDATE title
        SET dev_warehouse_path_id = (
            SELECT warehouse_path_id FROM title_warehouse_path
            WHERE title_warehouse_path.title_id = title.id AND path_type = 'dev'
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1 FROM title_warehouse_path
            WHERE title_warehouse_path.title_id = title.id AND path_type = 'dev'
        )
    """
    )

    op.execute(
        """
        UPDATE title
        SET prod_warehouse_path_id = (
            SELECT warehouse_path_id FROM title_warehouse_path
            WHERE title_warehouse_path.title_id = title.id AND path_type = 'prod'
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1 FROM title_warehouse_path
            WHERE title_warehouse_path.title_id = title.id AND path_type = 'prod'
        )
    """
    )

    # Add back foreign key constraints
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

    # Drop the junction table
    op.drop_table("title_warehouse_path")
