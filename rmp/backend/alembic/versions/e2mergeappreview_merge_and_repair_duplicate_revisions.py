"""Merge migration branches and repair duplicate legacy revisions.

Revision ID: e2mergeappreview
Revises: f8forum_safeguards, d1appreviewaudit
"""

from alembic import op
import sqlalchemy as sa


revision = "e2mergeappreview"
down_revision = ("f8forum_safeguards", "d1appreviewaudit")
branch_labels = None
depends_on = None


def _table_names():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade():
    """Restore tables skipped when duplicate revision IDs were deployed.

    The audit-origin migrations formerly reused the revision IDs assigned to
    the Survivor planner and shared game-line cache. Alembic could therefore
    mark either implementation as applied while skipping the other. The audit
    columns are repaired by ``d1appreviewaudit``; this merge repairs the two
    potentially skipped tables and leaves existing installations untouched.
    """

    tables = _table_names()

    if "survivor_entry_plans" not in tables:
        op.create_table(
            "survivor_entry_plans",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("entry_id", sa.String(length=36), nullable=False),
            sa.Column("week_num", sa.Integer(), nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "week_num >= 1 AND week_num <= 18",
                name="ck_survivor_entry_plans_week",
            ),
            sa.ForeignKeyConstraint(
                ["entry_id"], ["entries.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "entry_id",
                "week_num",
                name="uq_survivor_entry_plans_entry_week",
            ),
            sa.UniqueConstraint(
                "entry_id",
                "team_id",
                name="uq_survivor_entry_plans_entry_team",
            ),
        )
        op.create_index(
            "ix_survivor_entry_plans_entry_id",
            "survivor_entry_plans",
            ["entry_id"],
        )

    if "game_line_cache" not in tables:
        op.create_table(
            "game_line_cache",
            sa.Column("game_id", sa.Integer(), nullable=False),
            sa.Column("favorite_team_id", sa.Integer(), nullable=True),
            sa.Column("spread", sa.Float(), nullable=True),
            sa.Column("details", sa.String(length=64), nullable=True),
            sa.Column("provider", sa.String(length=64), nullable=True),
            sa.Column("fetched_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["favorite_team_id"], ["teams.id"]),
            sa.ForeignKeyConstraint(
                ["game_id"], ["schedule.game_id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("game_id"),
        )
        op.create_index(
            "ix_game_line_cache_fetched_at",
            "game_line_cache",
            ["fetched_at"],
        )


def downgrade():
    # This is a compatibility repair. Do not drop tables that may predate it.
    pass
