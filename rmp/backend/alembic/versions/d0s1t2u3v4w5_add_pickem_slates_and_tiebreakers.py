"""add pickem slates and tiebreakers

Revision ID: d0s1t2u3v4w5
Revises: c9r0s1t2u3v4
"""

from alembic import op
import sqlalchemy as sa


revision = "d0s1t2u3v4w5"
down_revision = "c9r0s1t2u3v4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pools",
        sa.Column("pickem_slate", sa.String(length=20), server_default="all", nullable=False),
    )
    op.create_check_constraint(
        "ck_pools_pickem_slate", "pools",
        "pickem_slate IN ('all', 'sunday', 'sunday_monday')",
    )
    op.create_table(
        "pickem_tiebreakers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entry_id", sa.String(length=36), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("predicted_total", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("predicted_total >= 0 AND predicted_total <= 200", name="ck_pickem_tiebreaker_total"),
        sa.ForeignKeyConstraint(["entry_id"], ["entries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entry_id", "week", name="uq_pickem_tiebreakers_entry_week"),
    )
    op.create_index("ix_pickem_tiebreakers_entry_id", "pickem_tiebreakers", ["entry_id"])


def downgrade():
    op.drop_index("ix_pickem_tiebreakers_entry_id", table_name="pickem_tiebreakers")
    op.drop_table("pickem_tiebreakers")
    op.drop_constraint("ck_pools_pickem_slate", "pools", type_="check")
    op.drop_column("pools", "pickem_slate")
