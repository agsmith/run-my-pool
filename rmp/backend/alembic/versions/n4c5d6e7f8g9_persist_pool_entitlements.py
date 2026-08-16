"""persist pool commissioner entitlements

Revision ID: n4c5d6e7f8g9
Revises: m3b4c5d6e7f8
"""

from alembic import op
import sqlalchemy as sa

revision = "n4c5d6e7f8g9"
down_revision = "m3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pools", sa.Column("billing_entitlement_id", sa.String(36), nullable=True))
    op.add_column("pools", sa.Column("billing_season", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_pools_billing_entitlement",
        "pools",
        "commissioner_entitlements",
        ["billing_entitlement_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_pools_billing_entitlement_id", "pools", ["billing_entitlement_id"])
    op.create_index("ix_pools_billing_season", "pools", ["billing_season"])


def downgrade():
    op.drop_index("ix_pools_billing_season", table_name="pools")
    op.drop_index("ix_pools_billing_entitlement_id", table_name="pools")
    op.drop_constraint("fk_pools_billing_entitlement", "pools", type_="foreignkey")
    op.drop_column("pools", "billing_season")
    op.drop_column("pools", "billing_entitlement_id")
