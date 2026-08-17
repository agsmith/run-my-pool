"""add owner pool report preferences

Revision ID: t0i1j2k3l4m5
Revises: s9h0i1j2k3l4
"""

from alembic import op
import sqlalchemy as sa


revision = "t0i1j2k3l4m5"
down_revision = "s9h0i1j2k3l4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pools", sa.Column("owner_reports_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.add_column("pools", sa.Column("owner_reports_frequency", sa.String(length=20), nullable=False, server_default="weekly"))
    op.add_column("pools", sa.Column("owner_reports_last_sent_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("pools", "owner_reports_last_sent_at")
    op.drop_column("pools", "owner_reports_frequency")
    op.drop_column("pools", "owner_reports_enabled")
