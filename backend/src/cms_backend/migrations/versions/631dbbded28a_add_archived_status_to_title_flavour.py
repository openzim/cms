"""add archived status to title flavour

Revision ID: 631dbbded28a
Revises: c58424978f8a
Create Date: 2026-10-15 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "631dbbded28a"
down_revision = "c58424978f8a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "title_flavour",
        sa.Column(
            "archived", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )


def downgrade():
    op.drop_column("title_flavour", "archived")
