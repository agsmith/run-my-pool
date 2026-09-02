"""add shared game line cache

Revision ID: b8q9r0s1t2u3
Revises: a7p8q9r0s1t2
"""

from alembic import op
import sqlalchemy as sa

revision = "b8q9r0s1t2u3"
down_revision = "a7p8q9r0s1t2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "game_line_cache",
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("favorite_team_id", sa.Integer(), nullable=True),
        sa.Column("spread", sa.Float(), nullable=True),
        sa.Column("details", sa.String(length=64), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["favorite_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(
            ["game_id"], ["schedule.game_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("game_id"),
    )
    op.create_index(
        "ix_game_line_cache_fetched_at", "game_line_cache", ["fetched_at"]
    )


def downgrade():
    op.drop_index(
        "ix_game_line_cache_fetched_at", table_name="game_line_cache"
    )
    op.drop_table("game_line_cache")
