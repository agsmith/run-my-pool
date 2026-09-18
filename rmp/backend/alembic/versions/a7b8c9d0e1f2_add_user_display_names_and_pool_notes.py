"""add user display names and pool member notes

Revision ID: a7b8c9d0e1f2
Revises: z6o7p8q9r0s1
"""

from alembic import op
import sqlalchemy as sa


revision = "a7b8c9d0e1f2"
down_revision = "z6o7p8q9r0s1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("display_name", sa.String(length=100), nullable=True))
    op.add_column("pool_members", sa.Column("notes", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("pool_members", "notes")
    op.drop_column("users", "display_name")
