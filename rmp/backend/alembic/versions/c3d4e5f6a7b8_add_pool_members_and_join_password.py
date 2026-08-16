"""add pool membership and private join passwords

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""

from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pools", sa.Column("join_password_hash", sa.String(255), nullable=True))
    op.create_table(
        "pool_members",
        sa.Column("pool_id", sa.String(36), sa.ForeignKey("pools.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
    )

    # Preserve current access: owners, delegated admins, and users who already
    # have entries are members when the new access model goes live.
    op.execute(
        "INSERT INTO pool_members (pool_id, user_id, joined_at) "
        "SELECT id, owner_id, COALESCE(created_at, CURRENT_TIMESTAMP) FROM pools "
        "WHERE owner_id IS NOT NULL"
    )
    op.execute(
        "INSERT INTO pool_members (pool_id, user_id, joined_at) "
        "SELECT pa.pool_id, pa.user_id, CURRENT_TIMESTAMP FROM pool_admins pa "
        "WHERE NOT EXISTS (SELECT 1 FROM pool_members pm "
        "WHERE pm.pool_id = pa.pool_id AND pm.user_id = pa.user_id)"
    )
    op.execute(
        "INSERT INTO pool_members (pool_id, user_id, joined_at) "
        "SELECT DISTINCT e.pool_id, e.user_id, CURRENT_TIMESTAMP FROM entries e "
        "WHERE e.pool_id IS NOT NULL AND e.user_id IS NOT NULL AND "
        "NOT EXISTS (SELECT 1 FROM pool_members pm "
        "WHERE pm.pool_id = e.pool_id AND pm.user_id = e.user_id)"
    )


def downgrade():
    op.drop_table("pool_members")
    op.drop_column("pools", "join_password_hash")
