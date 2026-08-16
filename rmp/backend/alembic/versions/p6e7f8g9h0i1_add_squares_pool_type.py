"""add squares pool type

Revision ID: p6e7f8g9h0i1
Revises: o5d6e7f8g9h0
"""

from alembic import op
import sqlalchemy as sa

revision = "p6e7f8g9h0i1"
down_revision = "o5d6e7f8g9h0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pools", sa.Column("squares_game_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_pools_squares_game", "pools", "schedule", ["squares_game_id"], ["game_id"])
    for name in ("home_q1_score", "away_q1_score", "home_half_score", "away_half_score", "home_q3_score", "away_q3_score"):
        op.add_column("schedule", sa.Column(name, sa.Integer(), nullable=True))

    op.create_table(
        "square_boards",
        sa.Column("pool_id", sa.String(36), nullable=False),
        sa.Column("home_digits", sa.String(32), nullable=True),
        sa.Column("away_digits", sa.String(32), nullable=True),
        sa.Column("total_pot_cents", sa.Integer(), nullable=True),
        sa.Column("q1_percent", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("halftime_percent", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("q3_percent", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("final_percent", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("locked_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["pool_id"], ["pools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["locked_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("pool_id"),
    )
    op.create_table(
        "square_claims",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("pool_id", sa.String(36), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("column_index", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("assigned_by", sa.String(36), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("claimed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["pool_id"], ["square_boards.pool_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pool_id", "row_index", "column_index", name="uq_square_claim_cell"),
    )
    op.create_index("ix_square_claims_pool_id", "square_claims", ["pool_id"])
    op.create_index("ix_square_claims_user_id", "square_claims", ["user_id"])
    op.create_table(
        "square_payouts",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("pool_id", sa.String(36), nullable=False),
        sa.Column("checkpoint", sa.String(16), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=False),
        sa.Column("away_score", sa.Integer(), nullable=False),
        sa.Column("winning_row", sa.Integer(), nullable=False),
        sa.Column("winning_column", sa.Integer(), nullable=False),
        sa.Column("winner_user_id", sa.String(36), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("determined_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["pool_id"], ["square_boards.pool_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pool_id", "checkpoint", name="uq_square_payout_checkpoint"),
    )
    op.create_index("ix_square_payouts_pool_id", "square_payouts", ["pool_id"])


def downgrade():
    op.drop_table("square_payouts")
    op.drop_table("square_claims")
    op.drop_table("square_boards")
    for name in ("away_q3_score", "home_q3_score", "away_half_score", "home_half_score", "away_q1_score", "home_q1_score"):
        op.drop_column("schedule", name)
    op.drop_constraint("fk_pools_squares_game", "pools", type_="foreignkey")
    op.drop_column("pools", "squares_game_id")
