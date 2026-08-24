import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

# Constants for foreign key relationships
USERS_ID_FK = "users.id"
POOLS_ID_FK = "pools.id"
ENTRIES_ID_FK = "entries.id"
TEAMS_ID_FK = "teams.id"
RULES_ID_FK = "rules.id"

Base = declarative_base()


def current_football_season() -> int:
    now = datetime.now(timezone.utc)
    return now.year - (1 if now.month <= 2 else 0)


class UserRole(enum.Enum):
    USER = "USER"
    POOL_ADMIN = "POOL_ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    abbrv = Column(String(10), nullable=False, unique=True)
    logo = Column(String(255))
    # relationships
    picks = relationship("Pick", back_populates="team_obj")


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(Enum(UserRole), default=UserRole.USER)
    mfa_enabled = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    # relationships
    pools = relationship("Pool", back_populates="owner")
    entries = relationship("Entry", back_populates="user")
    billing_orders = relationship("BillingOrder", back_populates="user")
    commissioner_entitlements = relationship(
        "CommissionerEntitlement", back_populates="user"
    )


class Pool(Base):
    __tablename__ = "pools"
    __table_args__ = (
        UniqueConstraint("name", name="uq_pools_name"),
        CheckConstraint(
            "survivor_mulligans >= 0 AND survivor_mulligans <= 3",
            name="ck_pools_survivor_mulligans_range",
        ),
    )
    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    pool_type = Column(String(20), nullable=False, default="survivor")
    survivor_mulligans = Column(Integer, nullable=False, default=0, server_default="0")
    pickem_games_per_week = Column(Integer, nullable=True)
    squares_game_id = Column(Integer, ForeignKey("schedule.game_id"), nullable=True)
    lock_time = Column(DateTime)
    lock_day_of_week = Column(Integer, nullable=True)
    lock_time_of_day = Column(Time, nullable=True)
    lock_timezone = Column(String(64), nullable=True)
    join_lock_time = Column(DateTime, nullable=True)
    is_private = Column(Boolean, default=False)
    join_password_hash = Column(String(255), nullable=True)
    join_password_encrypted = Column(Text, nullable=True)
    owner_id = Column(String(36), ForeignKey(USERS_ID_FK))
    billing_entitlement_id = Column(
        String(36),
        ForeignKey("commissioner_entitlements.id"),
        nullable=True,
        index=True,
    )
    billing_season = Column(Integer, nullable=True, index=True)
    owner_reports_enabled = Column(Boolean, nullable=False, default=False, server_default="0")
    owner_reports_frequency = Column(String(20), nullable=False, default="weekly", server_default="weekly")
    owner_reports_last_sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    # relationships
    owner = relationship("User", back_populates="pools")
    entries = relationship("Entry", back_populates="pool")
    pool_rules = relationship("PoolRule", back_populates="pool")
    pool_rule_values = relationship("PoolRuleValue", back_populates="pool")
    members = relationship(
        "PoolMember", back_populates="pool", cascade="all, delete-orphan"
    )
    billing_entitlement = relationship(
        "CommissionerEntitlement", back_populates="pools"
    )
    squares_game = relationship("Schedule", foreign_keys=[squares_game_id])
    square_games = relationship(
        "PoolSquareGame",
        back_populates="pool",
        cascade="all, delete-orphan",
        order_by="PoolSquareGame.display_order",
    )
    square_board = relationship(
        "SquareBoard", back_populates="pool", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def squares_game_ids(self):
        return [selection.game_id for selection in self.square_games]


class Rule(Base):
    __tablename__ = "rules"
    id = Column(String(36), primary_key=True, index=True)
    pool_type = Column(String(50))
    rule_text = Column(String(255))
    rule_type = Column(String(25))
    default_value = Column(String(25))
    enabled_by_default = Column(Boolean, default=True)
    # relationships
    pool_rules = relationship("PoolRule", back_populates="rule")
    pool_rule_values = relationship("PoolRuleValue", back_populates="rule")


class PoolRule(Base):
    __tablename__ = "pool_rules"
    pool_id = Column(String(36), ForeignKey(POOLS_ID_FK), primary_key=True)
    rule_id = Column(String(36), ForeignKey(RULES_ID_FK), primary_key=True)
    # relationships
    pool = relationship("Pool", back_populates="pool_rules")
    rule = relationship("Rule", back_populates="pool_rules")


class PoolRuleValue(Base):
    __tablename__ = "pool_rules_values"
    pool_id = Column(String(36), ForeignKey(POOLS_ID_FK), primary_key=True)
    rule_id = Column(String(36), ForeignKey(RULES_ID_FK), primary_key=True)
    rule_value = Column(String(255))
    # relationships
    pool = relationship("Pool", back_populates="pool_rule_values")
    rule = relationship("Rule", back_populates="pool_rule_values")


class Entry(Base):
    __tablename__ = "entries"
    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey(USERS_ID_FK))
    pool_id = Column(String(36), ForeignKey(POOLS_ID_FK))
    name = Column(String(255))
    alive = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    # relationships
    user = relationship("User", back_populates="entries")
    pool = relationship("Pool", back_populates="entries")
    picks = relationship("Pick", back_populates="entry")


class Pick(Base):
    __tablename__ = "picks"
    __table_args__ = (
        UniqueConstraint(
            "entry_id", "week", "game_id", name="uq_picks_entry_week_game"
        ),
    )
    id = Column(String(36), primary_key=True, index=True)
    entry_id = Column(String(36), ForeignKey(ENTRIES_ID_FK))
    week = Column(Integer)
    game_id = Column(Integer, ForeignKey("schedule.game_id"), nullable=True)
    team = Column(String(255))
    team_id = Column(Integer, ForeignKey(TEAMS_ID_FK))
    locked = Column(Boolean, default=False)
    result = Column(String(10))  # win, loss, pending
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    # relationships
    entry = relationship("Entry", back_populates="picks")
    team_obj = relationship("Team", back_populates="picks")
    game = relationship("Schedule", foreign_keys=[game_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey(USERS_ID_FK))
    action = Column(String(255))
    details = Column(Text)
    created_at = Column(DateTime)


class UsedPasswordResetToken(Base):
    __tablename__ = "used_password_reset_tokens"
    token_digest = Column(String(64), primary_key=True)
    used_at = Column(DateTime, nullable=False)


class PersistentSession(Base):
    __tablename__ = "persistent_sessions"
    token_digest = Column(String(64), primary_key=True)
    user_id = Column(String(36), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"
    token_digest = Column(String(64), primary_key=True)
    user_id = Column(String(36), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id = Column(String(36), primary_key=True)
    email = Column(String(255), index=True, nullable=False)
    attempted_at = Column(DateTime, index=True, nullable=False)


class MessageBoard(Base):
    __tablename__ = "message_board"
    id = Column(String(36), primary_key=True, index=True)
    pool_id = Column(String(36), ForeignKey(POOLS_ID_FK))
    user_id = Column(String(36), ForeignKey(USERS_ID_FK))
    message = Column(Text)
    created_at = Column(DateTime)


class PoolAdmin(Base):
    __tablename__ = "pool_admins"
    pool_id = Column(String(36), ForeignKey(POOLS_ID_FK), primary_key=True)
    user_id = Column(String(36), ForeignKey(USERS_ID_FK), primary_key=True)
    # relationships
    pool = relationship("Pool")
    user = relationship("User")


class PoolMember(Base):
    __tablename__ = "pool_members"
    pool_id = Column(
        String(36), ForeignKey(POOLS_ID_FK, ondelete="CASCADE"), primary_key=True
    )
    user_id = Column(String(36), ForeignKey(USERS_ID_FK), primary_key=True)
    joined_at = Column(DateTime, nullable=False)
    dues_paid = Column(Boolean, nullable=False, default=False, server_default="0")
    dues_updated_at = Column(DateTime, nullable=True)
    dues_updated_by = Column(String(36), ForeignKey(USERS_ID_FK), nullable=True)
    weekly_recap_enabled = Column(Boolean, nullable=False, default=False, server_default="0")

    pool = relationship("Pool", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])


class MemberRecapDelivery(Base):
    """One delivery attempt per member, pool, season, and completed week."""

    __tablename__ = "member_recap_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "pool_id", "user_id", "season", "week_num",
            name="uq_member_recap_delivery_pool_user_week",
        ),
    )
    id = Column(String(36), primary_key=True)
    pool_id = Column(String(36), ForeignKey(POOLS_ID_FK, ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False, index=True)
    season = Column(Integer, nullable=False)
    week_num = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    message_id = Column(String(255), nullable=True)
    attempted_at = Column(DateTime, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    error = Column(String(255), nullable=True)


class PoolUserLock(Base):
    __tablename__ = "pool_user_locks"
    pool_id = Column(String(36), ForeignKey(POOLS_ID_FK), primary_key=True)
    user_id = Column(String(36), ForeignKey(USERS_ID_FK), primary_key=True)
    locked_at = Column(DateTime, nullable=False)
    reason = Column(String(255), nullable=True)
    # relationships
    pool = relationship("Pool")
    user = relationship("User")


class Schedule(Base):
    __tablename__ = "schedule"
    __table_args__ = (
        Index("ix_schedule_week_start", "week_num", "start_time"),
        Index("ix_schedule_season_week_status", "season", "week_num", "status"),
        Index("ix_schedule_start_time", "start_time"),
    )
    game_id = Column(Integer, primary_key=True)
    season = Column(Integer, nullable=False, default=current_football_season)
    week_num = Column(Integer, nullable=False)
    home_team_id = Column(Integer, ForeignKey(TEAMS_ID_FK), nullable=False)
    away_team_id = Column(Integer, ForeignKey(TEAMS_ID_FK), nullable=False)
    start_time = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="scheduled")
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    home_q1_score = Column(Integer, nullable=True)
    away_q1_score = Column(Integer, nullable=True)
    home_half_score = Column(Integer, nullable=True)
    away_half_score = Column(Integer, nullable=True)
    home_q3_score = Column(Integer, nullable=True)
    away_q3_score = Column(Integer, nullable=True)
    winning_team_id = Column(Integer, nullable=True)
    result_updated_at = Column(DateTime, nullable=True)
    provider_updated_at = Column(DateTime, nullable=True)

    # relationships
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])


class PoolSquareGame(Base):
    """An ordered game selected for a multi-game Squares board."""

    __tablename__ = "pool_square_games"
    pool_id = Column(String(36), ForeignKey(POOLS_ID_FK, ondelete="CASCADE"), primary_key=True)
    game_id = Column(Integer, ForeignKey("schedule.game_id"), primary_key=True)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False)

    pool = relationship("Pool", back_populates="square_games")
    game = relationship("Schedule")


class SquareBoard(Base):
    """A 10x10 board shared by one or more selected games. Digits are absent until lock."""

    __tablename__ = "square_boards"
    pool_id = Column(String(36), ForeignKey(POOLS_ID_FK, ondelete="CASCADE"), primary_key=True)
    home_digits = Column(String(32), nullable=True)
    away_digits = Column(String(32), nullable=True)
    pot_mode = Column(String(16), nullable=False, default="fixed")
    total_pot_cents = Column(Integer, nullable=True)
    per_square_cents = Column(Integer, nullable=True)
    q1_percent = Column(Integer, nullable=False, default=25)
    halftime_percent = Column(Integer, nullable=False, default=25)
    q3_percent = Column(Integer, nullable=False, default=25)
    final_percent = Column(Integer, nullable=False, default=25)
    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(String(36), ForeignKey(USERS_ID_FK), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    pool = relationship("Pool", back_populates="square_board")
    claims = relationship("SquareClaim", back_populates="board", cascade="all, delete-orphan")
    payouts = relationship("SquarePayout", back_populates="board", cascade="all, delete-orphan")


class SquareClaim(Base):
    __tablename__ = "square_claims"
    __table_args__ = (
        UniqueConstraint("pool_id", "row_index", "column_index", name="uq_square_claim_cell"),
    )
    id = Column(String(36), primary_key=True)
    pool_id = Column(String(36), ForeignKey("square_boards.pool_id", ondelete="CASCADE"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False)
    column_index = Column(Integer, nullable=False)
    user_id = Column(String(36), ForeignKey(USERS_ID_FK), nullable=False, index=True)
    assigned_by = Column(String(36), ForeignKey(USERS_ID_FK), nullable=False)
    display_name = Column(String(100), nullable=True)
    claimed_at = Column(DateTime, nullable=False)

    board = relationship("SquareBoard", back_populates="claims")
    user = relationship("User", foreign_keys=[user_id])


class SquarePayout(Base):
    __tablename__ = "square_payouts"
    __table_args__ = (
        UniqueConstraint("pool_id", "game_id", "checkpoint", name="uq_square_payout_game_checkpoint"),
    )
    id = Column(String(36), primary_key=True)
    pool_id = Column(String(36), ForeignKey("square_boards.pool_id", ondelete="CASCADE"), nullable=False, index=True)
    game_id = Column(Integer, ForeignKey("schedule.game_id"), nullable=False, index=True)
    checkpoint = Column(String(16), nullable=False)
    home_score = Column(Integer, nullable=False)
    away_score = Column(Integer, nullable=False)
    winning_row = Column(Integer, nullable=False)
    winning_column = Column(Integer, nullable=False)
    winner_user_id = Column(String(36), ForeignKey(USERS_ID_FK), nullable=True)
    amount_cents = Column(Integer, nullable=True)
    determined_at = Column(DateTime, nullable=False)

    board = relationship("SquareBoard", back_populates="payouts")
    winner = relationship("User", foreign_keys=[winner_user_id])
    game = relationship("Schedule")


class UpdaterRun(Base):
    """Durable execution record for the scheduled NFL result updater."""

    __tablename__ = "updater_runs"
    id = Column(String(36), primary_key=True)
    job_name = Column(String(64), nullable=False, index=True)
    image_revision = Column(String(255), nullable=True)
    season = Column(Integer, nullable=True)
    week_num = Column(Integer, nullable=True)
    source = Column(String(32), nullable=False, default="espn")
    dry_run = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    games_fetched = Column(Integer, nullable=False, default=0)
    final_games = Column(Integer, nullable=False, default=0)
    games_changed = Column(Integer, nullable=False, default=0)
    picks_changed = Column(Integer, nullable=False, default=0)
    entries_changed = Column(Integer, nullable=False, default=0)
    discrepancies = Column(Integer, nullable=False, default=0)
    summary = Column(Text, nullable=True)
    error = Column(Text, nullable=True)


class PoolGameLine(Base):
    """Official point spread frozen when a pool's weekly picks lock."""

    __tablename__ = "pool_game_lines"
    pool_id = Column(String(36), ForeignKey(POOLS_ID_FK), primary_key=True)
    game_id = Column(Integer, ForeignKey("schedule.game_id"), primary_key=True)
    week_num = Column(Integer, nullable=False)
    favorite_team_id = Column(Integer, ForeignKey(TEAMS_ID_FK), nullable=True)
    spread = Column(Float, nullable=True)
    details = Column(String(64), nullable=True)
    provider = Column(String(64), nullable=False)
    captured_at = Column(DateTime, nullable=False)

    game = relationship("Schedule")
    favorite_team = relationship("Team")


class BillingOrder(Base):
    """A Stripe Checkout attempt and its fulfillment status."""

    __tablename__ = "billing_orders"
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey(USERS_ID_FK), nullable=False, index=True)
    plan = Column(String(32), nullable=False)
    order_type = Column(String(24), nullable=False, default="plan")
    quantity = Column(Integer, nullable=False, default=1)
    season = Column(Integer, nullable=False)
    status = Column(String(24), nullable=False, default="pending", index=True)
    stripe_checkout_session_id = Column(String(255), unique=True, nullable=True)
    stripe_payment_intent_id = Column(String(255), unique=True, nullable=True)
    stripe_customer_id = Column(String(255), nullable=True)
    amount_total = Column(Integer, nullable=True)
    currency = Column(String(8), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="billing_orders")


class CommissionerEntitlement(Base):
    """Highest commissioner plan granted to a user for a plan year."""

    __tablename__ = "commissioner_entitlements"
    __table_args__ = (
        UniqueConstraint("user_id", "season", name="uq_commissioner_entitlement_user_season"),
    )
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey(USERS_ID_FK), nullable=False, index=True)
    season = Column(Integer, nullable=False)
    plan = Column(String(32), nullable=False)
    status = Column(String(24), nullable=False, default="active")
    included_entries = Column(Integer, nullable=True)
    entry_block_count = Column(Integer, nullable=False, default=0)
    max_pools = Column(Integer, nullable=True)
    unlimited_entries = Column(Boolean, nullable=False, default=False)
    stripe_customer_id = Column(String(255), nullable=True)
    source_order_id = Column(
        String(36), ForeignKey("billing_orders.id"), nullable=False
    )
    activated_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="commissioner_entitlements")
    pools = relationship("Pool", back_populates="billing_entitlement")


class PlanYearPoolUsage(Base):
    """Permanent count of pool creations; deleting a pool never restores a slot."""

    __tablename__ = "plan_year_pool_usage"
    __table_args__ = (
        UniqueConstraint("user_id", "season", name="uq_plan_year_pool_usage_user_season"),
    )
    user_id = Column(String(36), ForeignKey(USERS_ID_FK), primary_key=True)
    season = Column(Integer, primary_key=True)
    pools_created = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class League(Base):
    """A named group of survivor pools managed together (optional feature)."""

    __tablename__ = "leagues"
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    lock_time = Column(DateTime, nullable=True)
    is_private = Column(Boolean, nullable=False, default=False)
    owner_id = Column(String(36), ForeignKey(USERS_ID_FK), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    owner = relationship("User")


class StripeWebhookEvent(Base):
    """Stripe event IDs already processed by the webhook."""

    __tablename__ = "stripe_webhook_events"
    id = Column(String(255), primary_key=True)
    event_type = Column(String(100), nullable=False)
    processed_at = Column(DateTime, nullable=False)
