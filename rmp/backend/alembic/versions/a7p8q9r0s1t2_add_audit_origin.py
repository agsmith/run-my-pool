"""Track request origin on audit events.

Revision ID: a7p8q9r0s1t2
Revises: z6o7p8q9r0s1
"""

from alembic import op
import sqlalchemy as sa

revision = "a7p8q9r0s1t2"
down_revision = "z6o7p8q9r0s1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("audit_logs", sa.Column("ip_address", sa.String(length=45), nullable=True))
    op.add_column("audit_logs", sa.Column("country", sa.String(length=2), nullable=True))


def downgrade():
    op.drop_column("audit_logs", "country")
    op.drop_column("audit_logs", "ip_address")
