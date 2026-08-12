"""Add Pick Em pool type and game-specific picks.

Revision ID: j0e1f2a3b4c5
Revises: i9d0e1f2a3b4
"""

from alembic import op
import sqlalchemy as sa

revision = "j0e1f2a3b4c5"
down_revision = "i9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pools",
        sa.Column("pool_type", sa.String(length=20), nullable=False, server_default="survivor"),
    )
    op.add_column("picks", sa.Column("game_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_picks_game_id", "picks", "schedule", ["game_id"], ["game_id"])
    op.create_unique_constraint(
        "uq_picks_entry_week_game", "picks", ["entry_id", "week", "game_id"]
    )


def downgrade():
    op.drop_constraint("uq_picks_entry_week_game", "picks", type_="unique")
    op.drop_constraint("fk_picks_game_id", "picks", type_="foreignkey")
    op.drop_column("picks", "game_id")
    op.drop_column("pools", "pool_type")
