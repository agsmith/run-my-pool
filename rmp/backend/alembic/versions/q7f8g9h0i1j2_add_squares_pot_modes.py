"""add squares pot modes

Revision ID: q7f8g9h0i1j2
Revises: p6e7f8g9h0i1
"""

from alembic import op
import sqlalchemy as sa


revision = "q7f8g9h0i1j2"
down_revision = "p6e7f8g9h0i1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("square_boards", sa.Column("pot_mode", sa.String(16), nullable=False, server_default="fixed"))
    op.add_column("square_boards", sa.Column("per_square_cents", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("square_boards", "per_square_cents")
    op.drop_column("square_boards", "pot_mode")
