"""initial_schema

Revision ID: 67ecb851b587
Revises:
Create Date: 2026-07-15 11:30:26.203320

NOTE: CHAR(36) -> VARCHAR(36) type normalization is intentionally omitted.
CHAR(36) and VARCHAR(36) are functionally identical for UUIDs in MySQL.
Altering FK-constrained columns requires dropping and re-adding constraints,
which is unnecessary churn for a no-op change.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "67ecb851b587"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Create pool_rules_values table (was missing from original schema)
    op.create_table(
        "pool_rules_values",
        sa.Column("pool_id", sa.String(length=36), nullable=False),
        sa.Column("rule_id", sa.String(length=36), nullable=False),
        sa.Column("rule_value", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["pool_id"], ["pools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["rules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("pool_id", "rule_id"),
    )

    # Add missing indexes (SQLAlchemy model index=True declarations)
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_entries_id"), "entries", ["id"], unique=False)
    op.create_index(op.f("ix_message_board_id"), "message_board", ["id"], unique=False)
    op.create_index(op.f("ix_picks_id"), "picks", ["id"], unique=False)
    op.create_index(op.f("ix_pools_id"), "pools", ["id"], unique=False)
    op.create_index(op.f("ix_rules_id"), "rules", ["id"], unique=False)
    op.create_index(op.f("ix_teams_id"), "teams", ["id"], unique=False)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # Remove stale schedule indexes (replaced by ix_* naming convention)
    op.drop_index("away_team", table_name="schedule")
    op.drop_index("home_team", table_name="schedule")

    # Remove stale users email index (replaced by ix_users_email above)
    op.drop_index("email", table_name="users")

    # Fix users.role enum: LEAGUE_ADMIN -> POOL_ADMIN
    op.alter_column(
        "users",
        "role",
        existing_type=mysql.ENUM("USER", "LEAGUE_ADMIN", "SUPER_ADMIN"),
        type_=sa.Enum("USER", "POOL_ADMIN", "SUPER_ADMIN", name="userrole"),
        existing_nullable=True,
        existing_server_default=sa.text("'USER'"),
    )

    # Seed static reference data — idempotent via ON DUPLICATE KEY UPDATE

    # NFL teams (32 teams + NT/LT sentinels)
    op.execute("""
        INSERT INTO teams (id, name, abbrv, logo) VALUES
        (1, 'Atlanta Falcons', 'ATL', '/nfl/atl.svg'),
        (2, 'Buffalo Bills', 'BUF', '/nfl/buf.svg'),
        (3, 'Chicago Bears', 'CHI', '/nfl/chi.svg'),
        (4, 'Cincinnati Bengals', 'CIN', '/nfl/cin.svg'),
        (5, 'Cleveland Browns', 'CLE', '/nfl/cle.svg'),
        (6, 'Dallas Cowboys', 'DAL', '/nfl/dal.svg'),
        (7, 'Denver Broncos', 'DEN', '/nfl/den.svg'),
        (8, 'Detroit Lions', 'DET', '/nfl/det.svg'),
        (9, 'Green Bay Packers', 'GB', '/nfl/gb.svg'),
        (10, 'Tennessee Titans', 'TEN', '/nfl/ten.svg'),
        (11, 'Indianapolis Colts', 'IND', '/nfl/ind.svg'),
        (12, 'Kansas City Chiefs', 'KC', '/nfl/kc.svg'),
        (13, 'Las Vegas Raiders', 'LV', '/nfl/lv.svg'),
        (14, 'Los Angeles Rams', 'LAR', '/nfl/lar.svg'),
        (15, 'Miami Dolphins', 'MIA', '/nfl/mia.svg'),
        (16, 'Minnesota Vikings', 'MIN', '/nfl/min.svg'),
        (17, 'New England Patriots', 'NE', '/nfl/ne.svg'),
        (18, 'New Orleans Saints', 'NO', '/nfl/no.svg'),
        (19, 'New York Giants', 'NYG', '/nfl/nyg.svg'),
        (20, 'New York Jets', 'NYJ', '/nfl/nyj.svg'),
        (21, 'Philadelphia Eagles', 'PHI', '/nfl/phi.svg'),
        (22, 'Arizona Cardinals', 'ARI', '/nfl/ari.svg'),
        (23, 'Pittsburgh Steelers', 'PIT', '/nfl/pit.svg'),
        (24, 'Los Angeles Chargers', 'LAC', '/nfl/lac.svg'),
        (25, 'San Francisco 49ers', 'SF', '/nfl/sf.svg'),
        (26, 'Seattle Seahawks', 'SEA', '/nfl/sea.svg'),
        (27, 'Tampa Bay Buccaneers', 'TB', '/nfl/tb.svg'),
        (28, 'Washington Commanders', 'WSH', '/nfl/wsh.svg'),
        (29, 'Carolina Panthers', 'CAR', '/nfl/car.svg'),
        (30, 'Jacksonville Jaguars', 'JAX', '/nfl/jax.svg'),
        (33, 'Baltimore Ravens', 'BAL', '/nfl/bal.svg'),
        (34, 'Houston Texans', 'HOU', '/nfl/hou.svg'),
        (98, 'Losing Team', 'LT', '/nfl/red_x.svg'),
        (99, 'No Team', 'NT', '/nfl/green_plus.svg')
        ON DUPLICATE KEY UPDATE name=VALUES(name), logo=VALUES(logo)
    """)

    # Survivor pool rules
    op.execute("""
        INSERT INTO rules (id, pool_type, rule_text, rule_type, default_value, enabled_by_default) VALUES
        ('weekly-lock-day', 'survivor', 'Weekly Lock Day', 'selection', '0', true),
        ('weekly-lock-time', 'survivor', 'Weekly Lock Time', 'time', '13:00:00', true),
        ('auto-pick-enabled', 'survivor', 'Auto-Pick Enabled', 'boolean', 'false', true),
        ('auto-pick-strategy', 'survivor', 'Auto-Pick Strategy', 'selection', 'random', true),
        ('game-mode', 'survivor', 'Game Mode', 'selection', 'pick_winner', true),
        ('message-board-enabled', 'survivor', 'Message Board Enabled', 'boolean', 'true', true)
        ON DUPLICATE KEY UPDATE rule_text=VALUES(rule_text), default_value=VALUES(default_value)
    """)


def downgrade() -> None:
    """Downgrade schema."""

    # Restore users.role enum to previous state
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum("USER", "POOL_ADMIN", "SUPER_ADMIN", name="userrole"),
        type_=mysql.ENUM("USER", "LEAGUE_ADMIN", "SUPER_ADMIN"),
        existing_nullable=True,
        existing_server_default=sa.text("'USER'"),
    )

    # Drop new-style indexes first before restoring old ones on same columns
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")

    # Restore stale indexes
    op.create_index("email", "users", ["email"], unique=True)
    op.create_index("home_team", "schedule", ["home_team_id"], unique=False)
    op.create_index("away_team", "schedule", ["away_team_id"], unique=False)

    # Drop remaining indexes added in upgrade
    op.drop_index(op.f("ix_teams_id"), table_name="teams")
    op.drop_index(op.f("ix_rules_id"), table_name="rules")
    op.drop_index(op.f("ix_pools_id"), table_name="pools")
    op.drop_index(op.f("ix_picks_id"), table_name="picks")
    op.drop_index(op.f("ix_message_board_id"), table_name="message_board")
    op.drop_index(op.f("ix_entries_id"), table_name="entries")
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")

    # Drop pool_rules_values table
    op.drop_table("pool_rules_values")
