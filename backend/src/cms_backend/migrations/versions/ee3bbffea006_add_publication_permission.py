"""add publication permission

Revision ID: ee3bbffea006
Revises: dd2aaceefda5
Create Date: 2026-10-29 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ee3bbffea006"
down_revision = "dd2aaceefda5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "publication_permission",
        sa.Column("title_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["title_id"],
            ["title.id"],
            name=op.f("fk_publication_permission_title_id_title"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["account.id"],
            name=op.f("fk_publication_permission_account_id_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "title_id", "account_id", name=op.f("pk_publication_permission")
        ),
    )


def downgrade():
    op.drop_table("publication_permission")
