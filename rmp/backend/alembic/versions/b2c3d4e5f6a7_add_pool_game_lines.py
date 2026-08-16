"""add pool game line snapshots

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pool_game_lines",
        sa.Column("pool_id", sa.String(36), sa.ForeignKey("pools.id"), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("schedule.game_id"), primary_key=True),
        sa.Column("week_num", sa.Integer(), nullable=False),
        sa.Column("favorite_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("spread", sa.Float(), nullable=True),
        sa.Column("details", sa.String(64), nullable=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("pool_game_lines")
