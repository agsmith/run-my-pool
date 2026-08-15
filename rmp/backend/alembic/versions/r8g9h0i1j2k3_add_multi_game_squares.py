"""add multi-game Squares boards

Revision ID: r8g9h0i1j2k3
Revises: q7f8g9h0i1j2
"""

from alembic import op
import sqlalchemy as sa


revision = "r8g9h0i1j2k3"
down_revision = "q7f8g9h0i1j2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pool_square_games",
        sa.Column("pool_id", sa.String(36), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["pool_id"], ["pools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["schedule.game_id"]),
        sa.PrimaryKeyConstraint("pool_id", "game_id"),
    )
    op.create_index("ix_pool_square_games_game_id", "pool_square_games", ["game_id"])
    op.execute(
        "INSERT INTO pool_square_games (pool_id, game_id, display_order, created_at) "
        "SELECT id, squares_game_id, 0, COALESCE(created_at, CURRENT_TIMESTAMP) "
        "FROM pools WHERE pool_type = 'squares' AND squares_game_id IS NOT NULL"
    )

    op.add_column("square_payouts", sa.Column("game_id", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE square_payouts sp JOIN pools p ON p.id = sp.pool_id "
        "SET sp.game_id = p.squares_game_id WHERE sp.game_id IS NULL"
    )
    op.alter_column("square_payouts", "game_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        "fk_square_payouts_game", "square_payouts", "schedule", ["game_id"], ["game_id"]
    )
    op.create_index("ix_square_payouts_game_id", "square_payouts", ["game_id"])
    op.drop_constraint("uq_square_payout_checkpoint", "square_payouts", type_="unique")
    op.create_unique_constraint(
        "uq_square_payout_game_checkpoint",
        "square_payouts",
        ["pool_id", "game_id", "checkpoint"],
    )


def downgrade():
    op.drop_constraint("uq_square_payout_game_checkpoint", "square_payouts", type_="unique")
    op.create_unique_constraint(
        "uq_square_payout_checkpoint", "square_payouts", ["pool_id", "checkpoint"]
    )
    op.drop_index("ix_square_payouts_game_id", table_name="square_payouts")
    op.drop_constraint("fk_square_payouts_game", "square_payouts", type_="foreignkey")
    op.drop_column("square_payouts", "game_id")
    op.drop_index("ix_pool_square_games_game_id", table_name="pool_square_games")
    op.drop_table("pool_square_games")
