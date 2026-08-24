"""add survivor mulligans

Revision ID: y5n6o7p8q9r0
Revises: x4m5n6o7p8q9
"""

from alembic import op
import sqlalchemy as sa

revision = "y5n6o7p8q9r0"
down_revision = "x4m5n6o7p8q9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pools",
        sa.Column(
            "survivor_mulligans",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "ck_pools_survivor_mulligans_range",
        "pools",
        "survivor_mulligans >= 0 AND survivor_mulligans <= 3",
    )


def downgrade():
    op.drop_constraint(
        "ck_pools_survivor_mulligans_range", "pools", type_="check"
    )
    op.drop_column("pools", "survivor_mulligans")
