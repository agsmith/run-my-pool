"""add recurring pick and league join lock times

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""

from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pools", sa.Column("lock_day_of_week", sa.Integer(), nullable=True))
    op.add_column("pools", sa.Column("lock_time_of_day", sa.Time(), nullable=True))
    op.add_column("pools", sa.Column("lock_timezone", sa.String(64), nullable=True))
    op.add_column("pools", sa.Column("join_lock_time", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("pools", "join_lock_time")
    op.drop_column("pools", "lock_timezone")
    op.drop_column("pools", "lock_time_of_day")
    op.drop_column("pools", "lock_day_of_week")
