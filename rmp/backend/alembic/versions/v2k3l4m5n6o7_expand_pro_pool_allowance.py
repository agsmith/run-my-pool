"""expand Pro plan pool allowance

Revision ID: v2k3l4m5n6o7
Revises: u1j2k3l4m5n6
"""

from alembic import op
import sqlalchemy as sa


revision = "v2k3l4m5n6o7"
down_revision = "u1j2k3l4m5n6"
branch_labels = None
depends_on = None


def upgrade():
    entitlements = sa.table(
        "commissioner_entitlements",
        sa.column("plan", sa.String()),
        sa.column("max_pools", sa.Integer()),
    )
    op.execute(
        entitlements.update()
        .where(entitlements.c.plan == "pro")
        .where(
            sa.or_(
                entitlements.c.max_pools.is_(None),
                entitlements.c.max_pools < 3,
            )
        )
        .values(max_pools=3)
    )


def downgrade():
    entitlements = sa.table(
        "commissioner_entitlements",
        sa.column("plan", sa.String()),
        sa.column("max_pools", sa.Integer()),
    )
    op.execute(
        entitlements.update()
        .where(entitlements.c.plan == "pro")
        .values(max_pools=1)
    )
