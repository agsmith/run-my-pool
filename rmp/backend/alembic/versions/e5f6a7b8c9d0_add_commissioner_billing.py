"""add commissioner billing and entitlements

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""

from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "billing_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan", sa.String(32), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("stripe_checkout_session_id", sa.String(255), nullable=True, unique=True),
        sa.Column("stripe_payment_intent_id", sa.String(255), nullable=True, unique=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("amount_total", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(8), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_billing_orders_user_id", "billing_orders", ["user_id"])
    op.create_index("ix_billing_orders_status", "billing_orders", ["status"])
    op.create_table(
        "commissioner_entitlements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("included_entries", sa.Integer(), nullable=True),
        sa.Column("max_pools", sa.Integer(), nullable=True),
        sa.Column("unlimited_entries", sa.Boolean(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("source_order_id", sa.String(36), sa.ForeignKey("billing_orders.id"), nullable=False),
        sa.Column("activated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "season", name="uq_commissioner_entitlement_user_season"),
    )
    op.create_index("ix_commissioner_entitlements_user_id", "commissioner_entitlements", ["user_id"])
    op.create_table(
        "stripe_webhook_events",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("stripe_webhook_events")
    op.drop_index("ix_commissioner_entitlements_user_id", table_name="commissioner_entitlements")
    op.drop_table("commissioner_entitlements")
    op.drop_index("ix_billing_orders_status", table_name="billing_orders")
    op.drop_index("ix_billing_orders_user_id", table_name="billing_orders")
    op.drop_table("billing_orders")
