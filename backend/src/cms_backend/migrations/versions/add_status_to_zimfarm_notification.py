"""Add status column to zimfarm_notification

Revision ID: add_status_to_notif
Revises: 6c6181d36517
Create Date: 2025-11-03 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_status_to_notif"
down_revision = "6c6181d36517"
branch_labels = None
depends_on = None


def upgrade():
    # Add status column with default value 'pending'
    op.add_column(
        "zimfarm_notification",
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
    )

    # Migrate existing data to status column based on processed/errored logic
    # Status logic:
    # - errored=true -> "errored"
    # - processed=true, errored=false, book_id is null -> "bad_notification"
    # - processed=true, errored=false, book_id is not null -> "processed"
    # - processed=false -> "pending"

    conn = op.get_bind()

    # Set status to "errored" where errored=true
    conn.execute(
        sa.text(
            "UPDATE zimfarm_notification SET status = 'errored' WHERE errored = true"
        )
    )

    # Set status to "bad_notification" where processed=true, errored=false, book_id
    # is null
    conn.execute(
        sa.text(
            "UPDATE zimfarm_notification SET status = 'bad_notification' "
            "WHERE processed = true AND errored = false AND book_id IS NULL"
        )
    )

    # Set status to "processed" where processed=true, errored=false, book_id is not
    # null
    conn.execute(
        sa.text(
            "UPDATE zimfarm_notification SET status = 'processed' "
            "WHERE processed = true AND errored = false AND book_id IS NOT NULL"
        )
    )

    # Set status to "pending" where processed=false (should already be default, but
    # explicit)
    conn.execute(
        sa.text(
            "UPDATE zimfarm_notification SET status = 'pending' WHERE processed = false"
        )
    )

    # Drop the old columns
    op.drop_column("zimfarm_notification", "processed")
    op.drop_column("zimfarm_notification", "errored")

    # Create partial indexes for pending and bad_notification status values
    # These indexes help efficiently query for notifications that need attention
    op.create_index(
        "idx_zimfarm_notification_status_pending",
        "zimfarm_notification",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )

    op.create_index(
        "idx_zimfarm_notification_status_bad_notification",
        "zimfarm_notification",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'bad_notification'"),
    )


def downgrade():
    # Drop the partial indexes
    op.drop_index(
        "idx_zimfarm_notification_status_bad_notification",
        table_name="zimfarm_notification",
    )
    op.drop_index(
        "idx_zimfarm_notification_status_pending",
        table_name="zimfarm_notification",
    )

    # Add back processed and errored columns
    op.add_column(
        "zimfarm_notification",
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "zimfarm_notification",
        sa.Column("errored", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Migrate data back from status to processed/errored
    conn = op.get_bind()

    # pending -> processed=false, errored=false
    conn.execute(
        sa.text(
            "UPDATE zimfarm_notification SET processed = false, errored = false "
            "WHERE status = 'pending'"
        )
    )

    # errored -> processed=true, errored=true
    conn.execute(
        sa.text(
            "UPDATE zimfarm_notification SET processed = true, errored = true "
            "WHERE status = 'errored'"
        )
    )

    # bad_notification -> processed=true, errored=false
    conn.execute(
        sa.text(
            "UPDATE zimfarm_notification SET processed = true, errored = false "
            "WHERE status = 'bad_notification'"
        )
    )

    # processed -> processed=true, errored=false
    conn.execute(
        sa.text(
            "UPDATE zimfarm_notification SET processed = true, errored = false "
            "WHERE status = 'processed'"
        )
    )

    # Drop status column
    op.drop_column("zimfarm_notification", "status")
