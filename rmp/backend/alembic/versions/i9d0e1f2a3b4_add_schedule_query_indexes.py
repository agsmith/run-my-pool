"""Add indexes used by current-season schedule queries.

Revision ID: i9d0e1f2a3b4
Revises: h8c9d0e1f2a3
"""

from alembic import op

revision = "i9d0e1f2a3b4"
down_revision = "h8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_schedule_week_start", "schedule", ["week_num", "start_time"])
    op.create_index("ix_schedule_start_time", "schedule", ["start_time"])


def downgrade():
    op.drop_index("ix_schedule_start_time", table_name="schedule")
    op.drop_index("ix_schedule_week_start", table_name="schedule")
