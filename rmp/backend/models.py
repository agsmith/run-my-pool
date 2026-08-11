from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    Text,
    Integer,
    Float,
    Time,
)
from sqlalchemy.orm import relationship, declarative_base
import enum

# Constants for foreign key relationships
USERS_ID_FK = "users.id"
POOLS_ID_FK = "pools.id"
ENTRIES_ID_FK = "entries.id"
TEAMS_ID_FK = "teams.id"
RULES_ID_FK = "rules.id"

Base = declarative_base()


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


class Pool(Base):
    __tablename__ = "pools"
    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    lock_time = Column(DateTime)
    lock_day_of_week = Column(Integer, nullable=True)
    lock_time_of_day = Column(Time, nullable=True)
    lock_timezone = Column(String(64), nullable=True)
    join_lock_time = Column(DateTime, nullable=True)
    is_private = Column(Boolean, default=False)
    join_password_hash = Column(String(255), nullable=True)
    owner_id = Column(String(36), ForeignKey(USERS_ID_FK))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    # relationships
    owner = relationship("User", back_populates="pools")
    entries = relationship("Entry", back_populates="pool")
    pool_rules = relationship("PoolRule", back_populates="pool")
    pool_rule_values = relationship("PoolRuleValue", back_populates="pool")
    members = relationship("PoolMember", back_populates="pool", cascade="all, delete-orphan")


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
    id = Column(String(36), primary_key=True, index=True)
    entry_id = Column(String(36), ForeignKey(ENTRIES_ID_FK))
    week = Column(Integer)
    team = Column(String(255))
    team_id = Column(Integer, ForeignKey(TEAMS_ID_FK))
    locked = Column(Boolean, default=False)
    result = Column(String(10))  # win, loss, pending
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    # relationships
    entry = relationship("Entry", back_populates="picks")
    team_obj = relationship("Team", back_populates="picks")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey(USERS_ID_FK))
    action = Column(String(255))
    details = Column(Text)
    created_at = Column(DateTime)


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
    pool_id = Column(String(36), ForeignKey(POOLS_ID_FK, ondelete="CASCADE"), primary_key=True)
    user_id = Column(String(36), ForeignKey(USERS_ID_FK), primary_key=True)
    joined_at = Column(DateTime, nullable=False)

    pool = relationship("Pool", back_populates="members")
    user = relationship("User")


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
    game_id = Column(Integer, primary_key=True)
    week_num = Column(Integer, nullable=False)
    home_team_id = Column(Integer, ForeignKey(TEAMS_ID_FK), nullable=False)
    away_team_id = Column(Integer, ForeignKey(TEAMS_ID_FK), nullable=False)
    start_time = Column(DateTime, nullable=False)
    winning_team_id = Column(Integer, nullable=True, default=99)

    # relationships
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])


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
