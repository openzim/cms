"""replace title maturity with manual review

Revision ID: d3e4f5a6b7c8
Revises: cfe262cb33db
Create Date: 2026-11-13 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d3e4f5a6b7c8"
down_revision = "cfe262cb33db"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "title",
        sa.Column(
            "manual_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.execute("UPDATE title SET manual_review = (maturity <> 'stable')")
    op.drop_index(op.f("ix_title_maturity"), table_name="title")
    op.drop_column("title", "maturity")
    op.create_index(
        op.f("ix_title_manual_review"), "title", ["manual_review"], unique=False
    )

    op.add_column(
        "title_history",
        sa.Column(
            "manual_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.execute("UPDATE title_history SET manual_review = (maturity <> 'stable')")
    op.drop_column("title_history", "maturity")

    op.add_column(
        "title_flavour",
        sa.Column(
            "temporary_manual_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade():
    op.drop_column("title_flavour", "temporary_manual_review")

    op.add_column(
        "title_history",
        sa.Column(
            "maturity",
            sa.String(),
            nullable=False,
            server_default="unstable",
        ),
    )
    op.execute(
        "UPDATE title_history "
        "SET maturity = CASE WHEN manual_review THEN 'unstable' ELSE 'stable' END"
    )
    op.alter_column("title_history", "maturity", server_default=None)
    op.drop_column("title_history", "manual_review")

    op.drop_index(op.f("ix_title_manual_review"), table_name="title")
    op.add_column(
        "title",
        sa.Column(
            "maturity",
            sa.String(),
            nullable=False,
            server_default="unstable",
        ),
    )
    op.execute(
        "UPDATE title "
        "SET maturity = CASE WHEN manual_review THEN 'unstable' ELSE 'stable' END"
    )
    op.alter_column("title", "maturity", server_default=None)
    op.drop_column("title", "manual_review")
    op.create_index(op.f("ix_title_maturity"), "title", ["maturity"], unique=False)
