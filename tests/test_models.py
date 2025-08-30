"""
Unit tests for database models in the Run My Pool application.
Tests the SQLAlchemy models and their relationships.
"""

import pytest
from datetime import datetime, timezone
from models import User_IAM, Users, Entries, Picks, Teams, Schedule, Weekly_Locks, League, User_Entitlements


class TestUserIAMModel:
    """Test User_IAM model functionality"""
    
    def test_create_user_iam(self, test_db):
        """Test creating a User_IAM record"""
        user = User_IAM(
            username="testuser",
            password="hashed_password",
            email="test@example.com",
            force_password_change=False,
            admin_role=False
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        assert user.user_id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.force_password_change is False
        assert user.admin_role is False
    
    def test_user_iam_unique_username(self, test_db):
        """Test username uniqueness constraint"""
        user1 = User_IAM(username="testuser", email="test1@example.com", password="pass1")
        user2 = User_IAM(username="testuser", email="test2@example.com", password="pass2")
        
        test_db.add(user1)
        test_db.commit()
        
        test_db.add(user2)
        with pytest.raises(Exception):  # Should raise integrity error
            test_db.commit()
    
    def test_user_iam_session_token(self, test_db):
        """Test session token functionality"""
        user = User_IAM(
            username="testuser",
            email="test@example.com",
            password="password",
            session_token="test_token_123"
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        assert user.session_token == "test_token_123"


class TestUsersModel:
    """Test Users model functionality"""
    
    def test_create_users_record(self, test_db):
        """Test creating a Users record"""
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
        
        assert user.user_id == 1
        assert user.name == "Test User"
        assert user.status == "active"
        assert user.paid is True
        assert user.admin is False
    
    def test_users_default_values(self, test_db):
        """Test default values for Users model"""
        user = Users(
            name="Test User",
            username="testuser"
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        assert user.paid is False  # Default value
        assert user.admin is False  # Default value


class TestEntriesModel:
    """Test Entries model functionality"""
    
    def test_create_entry(self, test_db):
        """Test creating an entry record"""
        entry = Entries(
            user_id=1,
            active_status="active",
            entry_name="Test Entry"
        )
        test_db.add(entry)
        test_db.commit()
        test_db.refresh(entry)
        
        assert entry.entry_id is not None
        assert entry.user_id == 1
        assert entry.active_status == "active"
        assert entry.entry_name == "Test Entry"
    
    def test_entry_default_status(self, test_db):
        """Test default active_status value"""
        entry = Entries(
            user_id=1,
            entry_name="Test Entry"
        )
        test_db.add(entry)
        test_db.commit()
        test_db.refresh(entry)
        
        assert entry.active_status == "active"  # Default value


class TestPicksModel:
    """Test Picks model functionality"""
    
    def test_create_pick(self, test_db):
        """Test creating a pick record"""
        pick = Picks(
            entry_id=1,
            team_id=2,
            week_num=1,
            result="open",
            game_id=101
        )
        test_db.add(pick)
        test_db.commit()
        test_db.refresh(pick)
        
        assert pick.pick_id is not None
        assert pick.entry_id == 1
        assert pick.team_id == 2
        assert pick.week_num == 1
        assert pick.result == "open"
        assert pick.game_id == 101
    
    def test_pick_default_result(self, test_db):
        """Test default result value"""
        pick = Picks(
            entry_id=1,
            team_id=2,
            week_num=1
        )
        test_db.add(pick)
        test_db.commit()
        test_db.refresh(pick)
        
        assert pick.result == "open"  # Default value


class TestTeamsModel:
    """Test Teams model functionality"""
    
    def test_create_team(self, test_db):
        """Test creating a team record"""
        team = Teams(
            team_id=1,
            name="New England Patriots",
            abbrv="NE",
            logo="ne.svg"
        )
        test_db.add(team)
        test_db.commit()
        test_db.refresh(team)
        
        assert team.team_id == 1
        assert team.name == "New England Patriots"
        assert team.abbrv == "NE"
        assert team.logo == "ne.svg"
    
    def test_bye_week_team(self, test_db):
        """Test creating the special BYE week team"""
        bye_team = Teams(
            team_id=99,
            name="BYE Week",
            abbrv="BYE",
            logo="bye.svg"
        )
        test_db.add(bye_team)
        test_db.commit()
        test_db.refresh(bye_team)
        
        assert bye_team.team_id == 99
        assert bye_team.name == "BYE Week"
        assert bye_team.abbrv == "BYE"


class TestScheduleModel:
    """Test Schedule model functionality"""
    
    def test_create_schedule_entry(self, test_db):
        """Test creating a schedule entry"""
        game_time = datetime(2025, 9, 7, 13, 0, tzinfo=timezone.utc)
        
        game = Schedule(
            game_id=1,
            week_num=1,
            home_team=1,
            away_team=2,
            start_time=game_time
        )
        test_db.add(game)
        test_db.commit()
        test_db.refresh(game)
        
        assert game.game_id == 1
        assert game.week_num == 1
        assert game.home_team == 1
        assert game.away_team == 2
        assert game.start_time == game_time


class TestWeeklyLocksModel:
    """Test Weekly_Locks model functionality"""
    
    def test_create_weekly_lock(self, test_db):
        """Test creating a weekly lock entry"""
        deadline = datetime(2025, 9, 7, 13, 0)
        
        lock = Weekly_Locks(
            week_num=1,
            deadline=deadline
        )
        test_db.add(lock)
        test_db.commit()
        test_db.refresh(lock)
        
        assert lock.week_num == 1
        assert lock.deadline == deadline
    
    def test_weekly_lock_primary_key(self, test_db):
        """Test that week_num is the primary key"""
        lock1 = Weekly_Locks(week_num=1, deadline=datetime(2025, 9, 7, 13, 0))
        lock2 = Weekly_Locks(week_num=1, deadline=datetime(2025, 9, 7, 14, 0))
        
        test_db.add(lock1)
        test_db.commit()
        
        test_db.add(lock2)
        with pytest.raises(Exception):  # Should raise integrity error
            test_db.commit()


class TestLeagueModel:
    """Test League model functionality"""
    
    def test_create_league(self, test_db):
        """Test creating a league record"""
        lock_time = datetime(2025, 9, 7, 13, 0)
        
        league = League(
            league_id=1,
            league_name="Test League",
            lock_time=lock_time
        )
        test_db.add(league)
        test_db.commit()
        test_db.refresh(league)
        
        assert league.league_id == 1
        assert league.league_name == "Test League"
        assert league.lock_time == lock_time


class TestUserEntitlementsModel:
    """Test User_Entitlements model functionality"""
    
    def test_create_user_entitlement(self, test_db):
        """Test creating a user entitlement record"""
        entitlement = User_Entitlements(
            user_id=1,
            league_id=1,
            status="active",
            role="player"
        )
        test_db.add(entitlement)
        test_db.commit()
        test_db.refresh(entitlement)
        
        assert entitlement.entitlement_id is not None
        assert entitlement.user_id == 1
        assert entitlement.league_id == 1
        assert entitlement.status == "active"
        assert entitlement.role == "player"


class TestModelRelationships:
    """Test relationships between models"""
    
    def test_user_picks_relationship(self, test_db):
        """Test the relationship between users, entries, and picks"""
        # Create user
        user = Users(user_id=1, name="Test User", username="testuser")
        test_db.add(user)
        test_db.commit()
        
        # Create entry
        entry = Entries(user_id=1, entry_name="Test Entry")
        test_db.add(entry)
        test_db.commit()
        test_db.refresh(entry)
        
        # Create picks
        pick1 = Picks(entry_id=entry.entry_id, team_id=1, week_num=1)
        pick2 = Picks(entry_id=entry.entry_id, team_id=2, week_num=2)
        test_db.add_all([pick1, pick2])
        test_db.commit()
        
        # Verify picks exist for the entry
        picks = test_db.query(Picks).filter(Picks.entry_id == entry.entry_id).all()
        assert len(picks) == 2
        assert picks[0].week_num in [1, 2]
        assert picks[1].week_num in [1, 2]
    
    def test_complete_data_flow(self, test_db):
        """Test a complete data flow from user creation to picks"""
        # Create team
        team = Teams(team_id=1, name="Test Team", abbrv="TT")
        test_db.add(team)
        
        # Create user
        user = Users(user_id=1, name="Test User", username="testuser")
        test_db.add(user)
        
        # Create entry
        entry = Entries(user_id=1, entry_name="Test Entry")
        test_db.add(entry)
        test_db.commit()
        test_db.refresh(entry)
        
        # Create schedule
        game = Schedule(
            game_id=1,
            week_num=1,
            home_team=1,
            away_team=2,
            start_time=datetime(2025, 9, 7, 13, 0, tzinfo=timezone.utc)
        )
        test_db.add(game)
        
        # Create pick
        pick = Picks(
            entry_id=entry.entry_id,
            team_id=1,
            week_num=1,
            game_id=1
        )
        test_db.add(pick)
        test_db.commit()
        
        # Verify complete data flow
        stored_pick = test_db.query(Picks).filter(Picks.pick_id == pick.pick_id).first()
        stored_team = test_db.query(Teams).filter(Teams.team_id == stored_pick.team_id).first()
        stored_game = test_db.query(Schedule).filter(Schedule.game_id == stored_pick.game_id).first()
        
        assert stored_pick is not None
        assert stored_team.name == "Test Team"
        assert stored_game.week_num == 1
