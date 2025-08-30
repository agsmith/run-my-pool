
from sqlalchemy import Boolean, Column, Integer, String, DateTime
from database import Base

# User_IAM table for authentication
class User_IAM(Base):
    __tablename__ = 'User_IAM'
    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(128), unique=True, index=True)
    password = Column(String(256))
    email = Column(String(256))
    session_token = Column(String(256))
    account_created_time = Column(DateTime)
    last_logged_in_time = Column(DateTime)
    force_password_change = Column(Boolean, default=False)
    admin_role = Column(Boolean, default=False)
    
    # Security enhancement columns
    salt = Column(String(255))
    session_token_expiry = Column(DateTime)
    failed_login_attempts = Column(Integer, default=0)
    last_login_attempt = Column(DateTime)
    password_changed_time = Column(DateTime)
    created_time = Column(DateTime)
    account_locked = Column(Boolean, default=False)
    account_locked_until = Column(DateTime)
    password_reset_token = Column(String(255))
    password_reset_token_expiry = Column(DateTime)

# User_Entitlements table
class User_Entitlements(Base):
    __tablename__ = 'User_Entitlements'
    entitlement_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    league_id = Column(Integer, index=True)
    status = Column(String(32))
    role = Column(String(32))

class League(Base):
    __tablename__ = 'League'
    league_id = Column(Integer, primary_key=True, index=True)
    league_name = Column(String(128), index=True)
    lock_time = Column(DateTime)

class Users(Base):
    __tablename__ = 'Users'
    user_id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, index=True)
    name = Column(String(128), unique=True, index=True)
    status = Column(String(32))
    paid = Column(Boolean, default=False)
    username = Column(String(128), unique=True, index=True)
    admin = Column(Boolean, default=False)

class Entries(Base):
    __tablename__ = 'Entries'
    entry_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    active_status = Column(String(32), default='active')
    entry_name = Column(String(128), index=True)

class Picks(Base):
    __tablename__ = 'Picks'
    pick_id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, index=True)
    team_id = Column(Integer, index=True)
    week_num = Column(Integer, index=True)
    result = Column(String(32), default='open')
    game_id = Column(Integer, index=True)


class Teams(Base):
    __tablename__ = 'Teams'
    team_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), index=True)
    abbrv = Column(String(8), index=True)
    logo = Column(String(256), index=True)

# Schedule table for weekly games
class Schedule(Base):
    __tablename__ = 'Schedule'
    game_id = Column(Integer, primary_key=True, index=True)
    week_num = Column(Integer, index=True, nullable=False)
    home_team = Column(Integer, index=True, nullable=False)
    away_team = Column(Integer, index=True, nullable=False)
    start_time = Column(DateTime, nullable=False)

# Weekly deadline management table
class Weekly_Locks(Base):
    __tablename__ = 'Weekly_Locks'
    week_num = Column(Integer, primary_key=True, index=True)
    deadline = Column(DateTime, nullable=False)