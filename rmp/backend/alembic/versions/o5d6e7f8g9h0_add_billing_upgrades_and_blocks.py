"""add billing upgrade and entry-block fields

Revision ID: o5d6e7f8g9h0
Revises: n4c5d6e7f8g9
"""

import sqlalchemy as sa

from alembic import op

revision = "o5d6e7f8g9h0"
down_revision = "n4c5d6e7f8g9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "billing_orders",
        sa.Column("order_type", sa.String(24), nullable=False, server_default="plan"),
    )
    op.add_column(
        "billing_orders",
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "commissioner_entitlements",
        sa.Column(
            "entry_block_count", sa.Integer(), nullable=False, server_default="0"
        ),
    )


def downgrade():
    op.drop_column("commissioner_entitlements", "entry_block_count")
    op.drop_column("billing_orders", "quantity")
    op.drop_column("billing_orders", "order_type")
