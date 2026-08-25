"""add survivor objective

Revision ID: z6o7p8q9r0s1
Revises: y5n6o7p8q9r0
"""

from alembic import op
import sqlalchemy as sa

revision = "z6o7p8q9r0s1"
down_revision = "y5n6o7p8q9r0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pools",
        sa.Column(
            "survivor_objective",
            sa.String(length=8),
            nullable=False,
            server_default="win",
        ),
    )
    op.create_check_constraint(
        "ck_pools_survivor_objective",
        "pools",
        "survivor_objective IN ('win', 'lose')",
    )


def downgrade():
    op.drop_constraint("ck_pools_survivor_objective", "pools", type_="check")
    op.drop_column("pools", "survivor_objective")
