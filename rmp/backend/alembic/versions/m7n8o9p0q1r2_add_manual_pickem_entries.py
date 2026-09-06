"""add manual pickem entries

Revision ID: m7n8o9p0q1r2
Revises: d0s1t2u3v4w5
"""

from alembic import op
import sqlalchemy as sa


revision = "m7n8o9p0q1r2"
down_revision = "d0s1t2u3v4w5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "entries",
        sa.Column("manual_participant_name", sa.String(length=100), nullable=True),
    )


def downgrade():
    op.drop_column("entries", "manual_participant_name")
