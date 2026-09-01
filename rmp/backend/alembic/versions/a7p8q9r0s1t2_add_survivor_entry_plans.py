"""add private survivor entry plans

Revision ID: a7p8q9r0s1t2
Revises: z6o7p8q9r0s1
"""

from alembic import op
import sqlalchemy as sa

revision = "a7p8q9r0s1t2"
down_revision = "z6o7p8q9r0s1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "survivor_entry_plans",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entry_id", sa.String(length=36), nullable=False),
        sa.Column("week_num", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("week_num >= 1 AND week_num <= 18", name="ck_survivor_entry_plans_week"),
        sa.ForeignKeyConstraint(["entry_id"], ["entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entry_id", "week_num", name="uq_survivor_entry_plans_entry_week"),
        sa.UniqueConstraint("entry_id", "team_id", name="uq_survivor_entry_plans_entry_team"),
    )
    op.create_index("ix_survivor_entry_plans_entry_id", "survivor_entry_plans", ["entry_id"])


def downgrade():
    op.drop_index("ix_survivor_entry_plans_entry_id", table_name="survivor_entry_plans")
    op.drop_table("survivor_entry_plans")
