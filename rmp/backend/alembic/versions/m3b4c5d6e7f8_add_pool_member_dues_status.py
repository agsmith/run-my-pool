"""Add pool-specific member dues status.

Revision ID: m3b4c5d6e7f8
Revises: l2a3b4c5d6e7
"""

from alembic import op
import sqlalchemy as sa


revision = "m3b4c5d6e7f8"
down_revision = "l2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pool_members",
        sa.Column("dues_paid", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("pool_members", sa.Column("dues_updated_at", sa.DateTime(), nullable=True))
    op.add_column("pool_members", sa.Column("dues_updated_by", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_pool_members_dues_updated_by_users",
        "pool_members",
        "users",
        ["dues_updated_by"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_pool_members_dues_updated_by_users", "pool_members", type_="foreignkey")
    op.drop_column("pool_members", "dues_updated_by")
    op.drop_column("pool_members", "dues_updated_at")
    op.drop_column("pool_members", "dues_paid")
