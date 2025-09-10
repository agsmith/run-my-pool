from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Text, Integer
from sqlalchemy.orm import relationship, declarative_base
import enum

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
    is_private = Column(Boolean, default=False)
    owner_id = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    # relationships
    owner = relationship("User", back_populates="pools")
    entries = relationship("Entry", back_populates="pool")

class Entry(Base):
    __tablename__ = "entries"
    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    pool_id = Column(String(36), ForeignKey("pools.id"))
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
    entry_id = Column(String(36), ForeignKey("entries.id"))
    week = Column(Integer)
    team = Column(String(255))  # Keep for backward compatibility
    team_id = Column(Integer, ForeignKey("teams.id"))  # New foreign key to teams
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
    user_id = Column(String(36), ForeignKey("users.id"))
    action = Column(String(255))
    details = Column(Text)
    created_at = Column(DateTime)

class MessageBoard(Base):
    __tablename__ = "message_board"
    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    message = Column(Text)
    created_at = Column(DateTime)

class PoolAdmin(Base):
    __tablename__ = "pool_admins"
    pool_id = Column(String(36), ForeignKey("pools.id"), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    # relationships
    pool = relationship("Pool")
    user = relationship("User")

class Schedule(Base):
    __tablename__ = "Schedule"
    game_id = Column(Integer, primary_key=True)
    week_num = Column(Integer, nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    winning_team_id = Column(String(100), nullable=False, default='99')
    
    # relationships
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
