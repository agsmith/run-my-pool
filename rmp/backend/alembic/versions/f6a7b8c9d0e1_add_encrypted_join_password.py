"""add encrypted join password

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
"""

from alembic import op
import sqlalchemy as sa


revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pools", sa.Column("join_password_encrypted", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("pools", "join_password_encrypted")
