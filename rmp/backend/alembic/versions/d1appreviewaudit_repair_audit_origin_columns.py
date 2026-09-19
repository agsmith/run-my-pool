"""Repair audit origin columns after duplicate legacy revision IDs.

Revision ID: d1appreviewaudit
Revises: a7b8c9d0e1f2
"""

from alembic import op
import sqlalchemy as sa


revision = "d1appreviewaudit"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def _column_names():
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("audit_logs")
    }


def upgrade():
    columns = _column_names()
    if "ip_address" not in columns:
        op.add_column(
            "audit_logs",
            sa.Column("ip_address", sa.String(length=45), nullable=True),
        )
    if "country" not in columns:
        op.add_column(
            "audit_logs",
            sa.Column("country", sa.String(length=2), nullable=True),
        )
    if "city" not in columns:
        op.add_column(
            "audit_logs",
            sa.Column("city", sa.String(length=128), nullable=True),
        )


def downgrade():
    columns = _column_names()
    if "city" in columns:
        op.drop_column("audit_logs", "city")
    if "country" in columns:
        op.drop_column("audit_logs", "country")
    if "ip_address" in columns:
        op.drop_column("audit_logs", "ip_address")
