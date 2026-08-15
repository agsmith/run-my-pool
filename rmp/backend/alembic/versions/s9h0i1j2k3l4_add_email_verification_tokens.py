"""add email verification tokens

Revision ID: s9h0i1j2k3l4
Revises: r8g9h0i1j2k3
"""

from alembic import op
import sqlalchemy as sa


revision = "s9h0i1j2k3l4"
down_revision = "r8g9h0i1j2k3"
branch_labels = None
depends_on = None


def upgrade():
    # Accounts created before this feature were allowed to sign in, so retain
    # that behavior while requiring verification for new registrations.
    op.execute("UPDATE users SET email_verified = 1 WHERE email_verified = 0 OR email_verified IS NULL")
    op.create_table(
        "email_verification_tokens",
        sa.Column("token_digest", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_digest"),
    )
    op.create_index("ix_email_verification_tokens_user_id", "email_verification_tokens", ["user_id"])
    op.create_index("ix_email_verification_tokens_created_at", "email_verification_tokens", ["created_at"])
    op.create_index("ix_email_verification_tokens_expires_at", "email_verification_tokens", ["expires_at"])


def downgrade():
    op.drop_index("ix_email_verification_tokens_expires_at", table_name="email_verification_tokens")
    op.drop_index("ix_email_verification_tokens_created_at", table_name="email_verification_tokens")
    op.drop_index("ix_email_verification_tokens_user_id", table_name="email_verification_tokens")
    op.drop_table("email_verification_tokens")
