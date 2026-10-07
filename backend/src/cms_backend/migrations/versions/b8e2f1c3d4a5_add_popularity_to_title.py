"""add popularity to title

Revision ID: b8e2f1c3d4a5
Revises: a4b2365eb87c
Create Date: 2026-10-07 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b8e2f1c3d4a5"
down_revision = "a4b2365eb87c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "title",
        sa.Column(
            "popularity",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
    )


def downgrade():
    op.drop_column("title", "popularity")
