"""Add authoritative game result metadata and updater run auditing.

Revision ID: l2a3b4c5d6e7
Revises: k1f2a3b4c5d6
"""

from alembic import op
import sqlalchemy as sa

revision = "l2a3b4c5d6e7"
down_revision = "k1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("schedule", sa.Column("season", sa.Integer(), nullable=True))
    op.add_column(
        "schedule",
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="scheduled"
        ),
    )
    op.add_column("schedule", sa.Column("home_score", sa.Integer(), nullable=True))
    op.add_column("schedule", sa.Column("away_score", sa.Integer(), nullable=True))
    op.add_column(
        "schedule", sa.Column("result_updated_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "schedule", sa.Column("provider_updated_at", sa.DateTime(), nullable=True)
    )

    # January and February games belong to the season that began the prior year.
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT game_id, start_time FROM schedule"))
    for game_id, start_time in rows:
        season = start_time.year - (1 if start_time.month <= 2 else 0)
        connection.execute(
            sa.text("UPDATE schedule SET season = :season WHERE game_id = :game_id"),
            {"season": season, "game_id": game_id},
        )
    op.execute(
        "UPDATE schedule SET status = 'final' "
        "WHERE winning_team_id IS NOT NULL AND winning_team_id <> 99"
    )
    op.execute("UPDATE schedule SET winning_team_id = NULL WHERE winning_team_id = 99")
    op.alter_column(
        "schedule",
        "winning_team_id",
        existing_type=sa.Integer(),
        nullable=True,
        server_default=None,
    )
    op.alter_column("schedule", "season", existing_type=sa.Integer(), nullable=False)
    op.create_index(
        "ix_schedule_season_week_status",
        "schedule",
        ["season", "week_num", "status"],
        unique=False,
    )

    op.create_table(
        "updater_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_name", sa.String(length=64), nullable=False),
        sa.Column("image_revision", sa.String(length=255), nullable=True),
        sa.Column("season", sa.Integer(), nullable=True),
        sa.Column("week_num", sa.Integer(), nullable=True),
        sa.Column(
            "source", sa.String(length=32), nullable=False, server_default="espn"
        ),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("games_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("final_games", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_changed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("picks_changed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("entries_changed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discrepancies", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_updater_runs_job_name", "updater_runs", ["job_name"])
    op.create_index("ix_updater_runs_status", "updater_runs", ["status"])


def downgrade():
    op.drop_index("ix_updater_runs_status", table_name="updater_runs")
    op.drop_index("ix_updater_runs_job_name", table_name="updater_runs")
    op.drop_table("updater_runs")
    op.drop_index("ix_schedule_season_week_status", table_name="schedule")
    op.execute("UPDATE schedule SET winning_team_id = 99 WHERE winning_team_id IS NULL")
    op.alter_column(
        "schedule",
        "winning_team_id",
        existing_type=sa.Integer(),
        nullable=True,
        server_default="99",
    )
    op.drop_column("schedule", "provider_updated_at")
    op.drop_column("schedule", "result_updated_at")
    op.drop_column("schedule", "away_score")
    op.drop_column("schedule", "home_score")
    op.drop_column("schedule", "status")
    op.drop_column("schedule", "season")
