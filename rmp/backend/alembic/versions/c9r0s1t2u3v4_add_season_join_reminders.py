"""add season join reminder delivery ledger

Revision ID: c9r0s1t2u3v4
Revises: b8q9r0s1t2u3
"""

from alembic import op
import sqlalchemy as sa

revision = "c9r0s1t2u3v4"
down_revision = "b8q9r0s1t2u3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "season_join_reminder_deliveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("attempted_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "season", name="uq_season_join_reminder_user_season"
        ),
    )
    op.create_index(
        "ix_season_join_reminder_deliveries_user_id",
        "season_join_reminder_deliveries",
        ["user_id"],
    )
    op.create_table(
        "season_entry_reminder_deliveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("attempted_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "season", name="uq_season_entry_reminder_user_season"
        ),
    )
    op.create_index(
        "ix_season_entry_reminder_deliveries_user_id",
        "season_entry_reminder_deliveries",
        ["user_id"],
    )
    op.create_table(
        "weekly_pick_reminder_deliveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week_num", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("attempted_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "season", "week_num", name="uq_weekly_pick_reminder_user_week"
        ),
    )
    op.create_index(
        "ix_weekly_pick_reminder_deliveries_user_id",
        "weekly_pick_reminder_deliveries",
        ["user_id"],
    )


def downgrade():
    op.drop_index(
        "ix_weekly_pick_reminder_deliveries_user_id",
        table_name="weekly_pick_reminder_deliveries",
    )
    op.drop_table("weekly_pick_reminder_deliveries")
    op.drop_index(
        "ix_season_entry_reminder_deliveries_user_id",
        table_name="season_entry_reminder_deliveries",
    )
    op.drop_table("season_entry_reminder_deliveries")
    op.drop_index(
        "ix_season_join_reminder_deliveries_user_id",
        table_name="season_join_reminder_deliveries",
    )
    op.drop_table("season_join_reminder_deliveries")
