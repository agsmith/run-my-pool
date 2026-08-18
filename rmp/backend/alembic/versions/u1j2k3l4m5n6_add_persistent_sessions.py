"""add persistent sessions

Revision ID: u1j2k3l4m5n6
Revises: t0i1j2k3l4m5
"""

from alembic import op
import sqlalchemy as sa


revision = "u1j2k3l4m5n6"
down_revision = "t0i1j2k3l4m5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "persistent_sessions",
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_digest"),
    )
    op.create_index("ix_persistent_sessions_user_id", "persistent_sessions", ["user_id"])
    op.create_index("ix_persistent_sessions_expires_at", "persistent_sessions", ["expires_at"])


def downgrade():
    op.drop_index("ix_persistent_sessions_expires_at", table_name="persistent_sessions")
    op.drop_index("ix_persistent_sessions_user_id", table_name="persistent_sessions")
    op.drop_table("persistent_sessions")
