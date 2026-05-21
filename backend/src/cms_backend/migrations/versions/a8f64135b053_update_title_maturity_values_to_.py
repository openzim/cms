"""update_title_maturity_values_to_unstable_and_stable

Revision ID: a8f64135b053
Revises: efb5f2ffd65f
Create Date: 2026-05-21 09:32:53.631838

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a8f64135b053"
down_revision = "efb5f2ffd65f"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE title
        SET maturity = 'unstable'
        WHERE maturity = 'dev'
    """)

    op.execute("""
        UPDATE title
        SET maturity = 'stable'
        WHERE maturity = 'robust'
    """)


def downgrade():
    op.execute("""
        UPDATE title
        SET maturity = 'dev'
        WHERE maturity = 'unstable'
    """)

    op.execute("""
        UPDATE title
        SET maturity = 'robust'
        WHERE maturity = 'stable'
    """)
