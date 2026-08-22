"""track plan-year pool creations

Revision ID: w3l4m5n6o7p8
Revises: v2k3l4m5n6o7
"""

from alembic import op
import sqlalchemy as sa

revision = "w3l4m5n6o7p8"
down_revision = "v2k3l4m5n6o7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "plan_year_pool_usage",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("pools_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "season"),
        sa.UniqueConstraint(
            "user_id", "season", name="uq_plan_year_pool_usage_user_season"
        ),
    )
    op.execute(sa.text("""
            INSERT INTO plan_year_pool_usage
                (user_id, season, pools_created, created_at, updated_at)
            SELECT owner_id, billing_season, COUNT(*), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM pools
            WHERE owner_id IS NOT NULL AND billing_season IS NOT NULL
            GROUP BY owner_id, billing_season
            """))


def downgrade():
    op.drop_table("plan_year_pool_usage")
