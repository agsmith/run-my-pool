"""add member weekly recap preferences and delivery ledger

Revision ID: x4m5n6o7p8q9
Revises: w3l4m5n6o7p8
"""

from alembic import op
import sqlalchemy as sa

revision = "x4m5n6o7p8q9"
down_revision = "w3l4m5n6o7p8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pool_members",
        sa.Column("weekly_recap_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.create_table(
        "member_recap_deliveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pool_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week_num", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("attempted_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["pool_id"], ["pools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pool_id", "user_id", "season", "week_num", name="uq_member_recap_delivery_pool_user_week"),
    )
    op.create_index("ix_member_recap_deliveries_pool_id", "member_recap_deliveries", ["pool_id"])
    op.create_index("ix_member_recap_deliveries_user_id", "member_recap_deliveries", ["user_id"])


def downgrade():
    op.drop_index("ix_member_recap_deliveries_user_id", table_name="member_recap_deliveries")
    op.drop_index("ix_member_recap_deliveries_pool_id", table_name="member_recap_deliveries")
    op.drop_table("member_recap_deliveries")
    op.drop_column("pool_members", "weekly_recap_enabled")
