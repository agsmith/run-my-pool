"""add_pool_user_locks_table

Revision ID: a1b2c3d4e5f6
Revises: 67ecb851b587
Create Date: 2026-08-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "67ecb851b587"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pool_user_locks",
        sa.Column(
            "pool_id", sa.String(36), sa.ForeignKey("pools.id"), primary_key=True
        ),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True
        ),
        sa.Column("locked_at", sa.DateTime, nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("pool_user_locks")
