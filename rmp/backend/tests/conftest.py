import pytest
import os
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

# Set environment variables BEFORE importing the app — database.py runs
# create_engine() at module load time and will attempt a MySQL connection
# unless DATABASE_URL is already pointing at SQLite.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DISABLE_WEEKLY_LOCK_WORKER", "1")
os.environ.setdefault("ENVIRONMENT", "development")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from deps import get_db
from models import Base, User, Pool, Entry, Team, Schedule, PoolAdmin
from passlib.context import CryptContext

# ---------------------------------------------------------------------------
# Function-scoped (existing) test database engine
# ---------------------------------------------------------------------------

# Create test database engine
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Session-scoped season simulation database engine
# ---------------------------------------------------------------------------

SEASON_DB_URL = "sqlite:///./test_season.db"
season_engine = create_engine(
    SEASON_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SeasonSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=season_engine)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db


# ---------------------------------------------------------------------------
# Season simulation helpers
# ---------------------------------------------------------------------------


def _load_2025_schedule():
    """Load the 2025 NFL regular season events from the bundled JSON."""
    schedule_path = Path(__file__).parent.parent / "nfl-schedule-2025.json"
    with open(schedule_path) as f:
        data = json.load(f)
    return [
        e
        for e in data["events"]
        if e["season"].get("year") == 2025
        and e["season"].get("slug") == "regular-season"
    ]


def _extract_teams_from_events(events):
    """Return a dict of {team_id: {id, name, abbrv}} from schedule events."""
    teams = {}
    for e in events:
        c = e["competitions"][0]
        for comp in c["competitors"]:
            t = comp["team"]
            tid = int(t["id"])
            if tid not in teams:
                teams[tid] = {
                    "id": tid,
                    "name": t["displayName"],
                    "abbrv": t["abbreviation"],
                }
    return teams


def seed_season_schedule(db, events):
    """
    Seed Team and Schedule rows into db from 2025 regular season events.
    Idempotent — uses merge so it can be called multiple times safely.
    """
    teams_data = _extract_teams_from_events(events)

    # Upsert teams
    for td in teams_data.values():
        team = Team(id=td["id"], name=td["name"], abbrv=td["abbrv"], logo=None)
        db.merge(team)
    db.flush()

    # Build a game_id counter (ESPN event IDs are large ints; use a local sequence)
    game_counter = 1
    for e in sorted(events, key=lambda x: x["date"]):
        c = e["competitions"][0]
        home_team_id = next(
            int(comp["team"]["id"])
            for comp in c["competitors"]
            if comp["homeAway"] == "home"
        )
        away_team_id = next(
            int(comp["team"]["id"])
            for comp in c["competitors"]
            if comp["homeAway"] == "away"
        )
        week_num = e["week"]["number"]
        start_time_str = c.get("startDate") or e["date"]
        # Parse ISO 8601 (e.g. "2025-09-05T00:20Z")
        start_time_str = start_time_str.replace("Z", "")
        if "." in start_time_str:
            start_time_str = start_time_str.split(".")[0]
        start_time = datetime.fromisoformat(start_time_str)

        game = Schedule(
            game_id=game_counter,
            week_num=week_num,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            start_time=start_time,
            winning_team_id=None,
        )
        db.merge(game)
        game_counter += 1

    db.commit()
    return game_counter - 1  # number of games seeded


def create_season_users_and_entries(db, pool_id):
    """
    Create 750 users and 2000 entries in pool_id.
    First 500 users get 3 entries each (1500), last 250 get 2 each (500) = 2000 total.
    Returns (users_list, entries_list).
    """
    users = []
    entries = []
    hashed_pw = _pwd_context.hash("SeasonPass123!")

    for i in range(750):
        user = User(
            id=str(uuid.uuid4()),
            email=f"season_user_{i:04d}@test.runmypool.net",
            hashed_password=hashed_pw,
            is_active=True,
        )
        db.add(user)
        users.append(user)

        entry_count = 3 if i < 500 else 2
        for j in range(entry_count):
            entry = Entry(
                id=str(uuid.uuid4()),
                user_id=user.id,
                pool_id=pool_id,
                name=f"Entry-{i:04d}-{j}",
                alive=True,
                created_at=datetime(2025, 8, 1),
                updated_at=datetime(2025, 8, 1),
            )
            db.add(entry)
            entries.append(entry)

    db.commit()
    return users, entries


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
    return {"email": "test@example.com", "password": "TestPassword123!"}


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


# ---------------------------------------------------------------------------
# Session-scoped season simulation fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def nfl_schedule_2025():
    """Load 2025 NFL regular season events from the bundled JSON (session-scoped)."""
    return _load_2025_schedule()


@pytest.fixture(scope="session")
def season_db(nfl_schedule_2025):
    """
    Session-scoped SQLAlchemy session for the full season simulation.
    Creates all tables once, seeds the schedule, yields the session,
    and drops all tables on teardown.
    """
    # Ensure env vars are set for this session
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DATABASE_URL"] = SEASON_DB_URL

    Base.metadata.create_all(bind=season_engine)
    db = SeasonSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=season_engine)
        # Remove leftover db file
        if os.path.exists("./test_season.db"):
            os.remove("./test_season.db")


@pytest.fixture(scope="session")
def season_client(season_db):
    """
    Session-scoped TestClient wired to the season_db via dependency override.
    """

    def _override():
        yield season_db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    # Restore the standard function-scoped override
    app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def season_pool(season_client, season_db):
    """
    Session-scoped pool owned by a dedicated admin user.
    lock_time is None initially; tests set it as needed.
    """
    # Create pool admin user
    admin_email = "season_admin@test.runmypool.net"
    reg_resp = season_client.post(
        "/auth/register",
        json={"email": admin_email, "password": "AdminPass123!"},
    )
    assert reg_resp.status_code == 200, reg_resp.text

    login_resp = season_client.post(
        "/auth/login",
        json={"email": admin_email, "password": "AdminPass123!"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]

    pool_resp = season_client.post(
        "/pools/create",
        json={
            "name": "2025 Season Survivor Pool",
            "description": "Full season test",
            "is_private": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert pool_resp.status_code == 200, pool_resp.text

    return {
        "pool_id": pool_resp.json()["id"],
        "admin_token": admin_token,
        "admin_email": admin_email,
    }


@pytest.fixture(scope="session")
def season_fixture(season_db, season_pool, nfl_schedule_2025):
    """
    Session-scoped fixture that seeds the full 2025 schedule and creates
    750 users with 2000 entries in the season pool.

    Returns a dict with:
        pool_id, admin_token, users, entries, games (Schedule objects)
    """
    pool_id = season_pool["pool_id"]

    # Seed schedule (teams + games)
    game_count = seed_season_schedule(season_db, nfl_schedule_2025)

    # Create users and entries
    users, entries = create_season_users_and_entries(season_db, pool_id)

    # Fetch all seeded games
    from models import Schedule

    games = (
        season_db.query(Schedule).order_by(Schedule.week_num, Schedule.game_id).all()
    )

    return {
        "pool_id": pool_id,
        "admin_token": season_pool["admin_token"],
        "admin_email": season_pool["admin_email"],
        "users": users,
        "entries": entries,
        "games": games,
        "game_count": game_count,
    }
