"""Persistent forum reports, personal blocks, and pool posting suspensions."""

from alembic import op
import sqlalchemy as sa

revision = "f8forum_safeguards"
down_revision = "m7n8o9p0q1r2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "forum_blocks",
        sa.Column(
            "blocker_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "blocked_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "forum_bans",
        sa.Column(
            "pool_id",
            sa.String(36),
            sa.ForeignKey("pools.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "forum_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "pool_id",
            sa.String(36),
            sa.ForeignKey("pools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("message_id", sa.String(36), nullable=False),
        sa.Column(
            "reporter_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("message_snapshot", sa.Text(), nullable=False),
        sa.Column("reason", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime()),
        sa.Column("resolved_by", sa.String(36)),
        sa.UniqueConstraint("message_id", "reporter_id", name="uq_forum_report_member"),
    )
    op.create_index("ix_forum_reports_pool_id", "forum_reports", ["pool_id"])


def downgrade():
    op.drop_table("forum_reports")
    op.drop_table("forum_bans")
    op.drop_table("forum_blocks")
