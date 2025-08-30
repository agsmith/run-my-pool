"""
Test configuration and fixtures for Run My Pool application.
This module provides shared test utilities and fixtures.
"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch
import base64
import hashlib
import secrets

# Import the application
import sys
sys.path.append('..')
from main import app, get_db
from database import Base
from models import User_IAM, Users, Entries, Picks, Teams, Schedule, Weekly_Locks


# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def test_client():
    """Create a test client for the FastAPI application"""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after the test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_user_iam(test_db):
    """Create a sample User_IAM record with secure bcrypt password"""
    from security_config import PasswordSecurity
    
    # Generate secure password hash and salt
    hashed_password, salt = PasswordSecurity.hash_password("password123")
    
    user = User_IAM(
        user_id=1,
        username="testuser",
        password=hashed_password,
        salt=salt,
        email="test@example.com",
        session_token=None,
        force_password_change=False,
        admin_role=False,
        failed_login_attempts=0,
        account_locked=False
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def sample_admin_user(test_db):
    """Create a sample admin User_IAM record with secure bcrypt password"""
    from security_config import PasswordSecurity
    
    # Generate secure password hash and salt
    hashed_password, salt = PasswordSecurity.hash_password("adminpass123")
    
    user = User_IAM(
        user_id=2,
        username="adminuser",
        password=hashed_password,
        salt=salt,
        email="admin@example.com",
        session_token=None,
        force_password_change=False,
        admin_role=True,
        failed_login_attempts=0,
        account_locked=False
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def sample_users_record(test_db):
    """Create a sample Users record"""
    user = Users(
        user_id=1,
        league_id=1,
        name="Test User",
        status="active",
        paid=True,
        username="testuser",
        admin=False
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def sample_admin_users_record(test_db):
    """Create a sample admin Users record"""
    user = Users(
        user_id=2,
        league_id=1,
        name="Admin User",
        status="active",
        paid=True,
        username="adminuser",
        admin=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def sample_entry(test_db, sample_users_record):
    """Create a sample Entry record"""
    entry = Entries(
        entry_id=1,
        user_id=sample_users_record.user_id,
        active_status="active",
        entry_name="Test Entry"
    )
    test_db.add(entry)
    test_db.commit()
    test_db.refresh(entry)
    return entry


@pytest.fixture
def sample_teams(test_db):
    """Create sample team records"""
    teams = [
        Teams(team_id=1, name="New England Patriots", abbrv="NE", logo="ne.svg"),
        Teams(team_id=2, name="Dallas Cowboys", abbrv="DAL", logo="dal.svg"),
        Teams(team_id=3, name="Green Bay Packers", abbrv="GB", logo="gb.svg"),
        Teams(team_id=99, name="BYE Week", abbrv="BYE", logo="bye.svg"),
    ]
    test_db.add_all(teams)
    test_db.commit()
    return teams


@pytest.fixture
def sample_picks(test_db, sample_entry, sample_teams):
    """Create sample pick records"""
    picks = [
        Picks(pick_id=1, entry_id=sample_entry.entry_id, team_id=1, week_num=1, result="open", game_id=1),
        Picks(pick_id=2, entry_id=sample_entry.entry_id, team_id=2, week_num=2, result="open", game_id=2),
        Picks(pick_id=3, entry_id=sample_entry.entry_id, team_id=99, week_num=3, result="open", game_id=None),
    ]
    test_db.add_all(picks)
    test_db.commit()
    return picks


@pytest.fixture
def sample_schedule(test_db, sample_teams):
    """Create sample schedule records"""
    from datetime import datetime, timezone
    
    schedule_entries = [
        Schedule(
            game_id=1, 
            week_num=1, 
            home_team=1, 
            away_team=2, 
            start_time=datetime(2025, 9, 7, 13, 0, tzinfo=timezone.utc)
        ),
        Schedule(
            game_id=2, 
            week_num=2, 
            home_team=2, 
            away_team=3, 
            start_time=datetime(2025, 9, 14, 16, 30, tzinfo=timezone.utc)
        ),
    ]
    test_db.add_all(schedule_entries)
    test_db.commit()
    return schedule_entries


@pytest.fixture
def sample_weekly_locks(test_db):
    """Create sample weekly lock records"""
    from datetime import datetime
    
    locks = [
        Weekly_Locks(week_num=1, deadline=datetime(2025, 9, 7, 13, 0)),
        Weekly_Locks(week_num=2, deadline=datetime(2025, 9, 14, 13, 0)),
    ]
    test_db.add_all(locks)
    test_db.commit()
    return locks


def create_session_cookie(username: str, session_token: str) -> str:
    """Helper function to create a valid session cookie using new format"""
    from datetime import datetime
    timestamp = datetime.utcnow().isoformat()
    session_data = f"{username}|{session_token}|{timestamp}"
    return base64.b64encode(session_data.encode()).decode()


@pytest.fixture
def authenticated_user_cookie(test_db, sample_user_iam):
    """Create a session cookie for an authenticated user"""
    session_token = secrets.token_urlsafe(32)
    sample_user_iam.session_token = session_token
    test_db.commit()
    return create_session_cookie(sample_user_iam.username, session_token)


@pytest.fixture
def authenticated_admin_cookie(test_db, sample_admin_user):
    """Create a session cookie for an authenticated admin user"""
    session_token = secrets.token_urlsafe(32)
    sample_admin_user.session_token = session_token
    test_db.commit()
    return create_session_cookie(sample_admin_user.username, session_token)


class TestHelpers:
    """Helper methods for testing"""
    
    @staticmethod
    def create_test_user(db, username="testuser", email="test@example.com", password="password123", admin=False):
        """Create a test user in both User_IAM and Users tables"""
        from security_config import PasswordSecurity
        
        # Generate secure password hash and salt
        hashed_password, salt = PasswordSecurity.hash_password(password)
        
        # Create User_IAM record
        user_iam = User_IAM(
            username=username,
            password=hashed_password,
            salt=salt,
            email=email,
            admin_role=admin,
            force_password_change=False,
            failed_login_attempts=0,
            account_locked=False
        )
        db.add(user_iam)
        db.flush()
        
        # Create Users record
        user = Users(
            user_id=user_iam.user_id,
            name=f"Test {username}",
            username=username,
            admin=admin,
            status="active",
            paid=True,
            league_id=1
        )
        db.add(user)
        db.commit()
        
        return user_iam, user
    
    @staticmethod
    def login_user(client, username="testuser", password="password123"):
        """Helper to log in a user and return session cookie"""
        response = client.post(
            "/login",
            data={"username": username, "password": password}
        )
        return response.cookies.get("session-token")
