"""Track originating city on audit events.

Revision ID: b8q9r0s1t2u3
Revises: a7p8q9r0s1t2
"""

from alembic import op
import sqlalchemy as sa

revision = "b8q9r0s1t2u3"
down_revision = "a7p8q9r0s1t2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("audit_logs", sa.Column("city", sa.String(length=128), nullable=True))


def downgrade():
    op.drop_column("audit_logs", "city")
