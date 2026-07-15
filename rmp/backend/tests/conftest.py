import pytest
import os

# Set environment variables BEFORE importing the app — database.py runs
# create_engine() at module load time and will attempt a MySQL connection
# unless DATABASE_URL is already pointing at SQLite.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from deps import get_db
from models import Base

# Create test database engine
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    """Create test client for FastAPI app"""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as client:
        yield client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Create database session for testing"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
    return {"email": "test@example.com", "password": "testpassword123"}


@pytest.fixture
def test_pool_data():
    """Sample pool data for testing"""
    return {
        "name": "Test Pool",
        "description": "A test pool for testing",
        "is_private": False,
        "rule_values": [
            {"rule_id": "weekly-lock-day", "rule_value": "4"},
            {"rule_id": "weekly-lock-time", "rule_value": "17:00:00"},
            {"rule_id": "game-mode", "rule_value": "pick_winner"},
        ],
    }


@pytest.fixture
def authenticated_client(client, test_user_data):
    """Create authenticated client with test user"""
    # Register user
    response = client.post("/auth/register", json=test_user_data)
    assert response.status_code == 200

    # Login user
    login_response = client.post(
        "/auth/login",
        json={"email": test_user_data["email"], "password": test_user_data["password"]},
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    return client, login_response.json()


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables"""
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    yield
    # Cleanup after test
    if "SECRET_KEY" in os.environ:
        del os.environ["SECRET_KEY"]
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]
