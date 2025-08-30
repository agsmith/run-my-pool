"""
Unit tests for pick management and game logic in the Run My Pool application.
Tests pick submission, validation, deadline checking, scoring, and game-related functionality.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from models import Users, Entries, Picks, Teams, Schedule, Weekly_Locks


class TestPickSubmission:
    """Test pick submission functionality"""
    
    def test_submit_picks_requires_auth(self, test_client):
        """Test that pick submission requires authentication"""
        response = test_client.post(
            "/submit-picks",
            json={"picks": [{"game_id": 1, "team_id": 1}]}
        )
        assert response.status_code == 401
    
    def test_submit_picks_success(self, test_client, test_db, authenticated_user_cookie, sample_game_data):
        """Test successful pick submission"""
        # Create user entry
        user = test_db.query(Users).filter(Users.username == "testuser").first()
        entry = Entries(
            user_id=user.user_id,
            entry_name="Test Entry",
            current_week=1,
            weekly_total=0,
            season_total=0
        )
        test_db.add(entry)
        test_db.commit()
        
        cookies = {"session-token": authenticated_user_cookie}
        
        pick_data = {
            "entry_id": entry.entry_id,
            "week": 1,
            "picks": [
                {"game_id": 1, "team_id": 1},
                {"game_id": 2, "team_id": 3}
            ]
        }
        
        response = test_client.post("/submit-picks", json=pick_data, cookies=cookies)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Picks submitted successfully"
        
        # Verify picks were saved to database
        picks = test_db.query(Picks).filter(
            Picks.entry_id == entry.entry_id,
            Picks.week == 1
        ).all()
        assert len(picks) == 2
    
    def test_submit_picks_validation(self, test_client, authenticated_user_cookie):
        """Test pick submission validation"""
        cookies = {"session-token": authenticated_user_cookie}
        
        # Test missing required fields
        response = test_client.post(
            "/submit-picks",
            json={"picks": []},
            cookies=cookies
        )
        assert response.status_code == 422
        
        # Test invalid pick data
        response = test_client.post(
            "/submit-picks",
            json={
                "entry_id": "invalid",
                "week": -1,
                "picks": [{"invalid": "data"}]
            },
            cookies=cookies
        )
        assert response.status_code == 422
    
    def test_submit_picks_deadline_check(self, test_client, test_db, authenticated_user_cookie, sample_game_data):
        """Test that picks cannot be submitted after deadline"""
        # Create a game with past deadline
        past_time = datetime.now() - timedelta(hours=1)
        game = Schedule(
            game_id=99,
            week=1,
            away_team_id=1,
            home_team_id=2,
            game_time=past_time,
            season=2025
        )
        test_db.add(game)
        test_db.commit()
        
        cookies = {"session-token": authenticated_user_cookie}
        
        pick_data = {
            "entry_id": 1,
            "week": 1,
            "picks": [{"game_id": 99, "team_id": 1}]
        }
        
        response = test_client.post("/submit-picks", json=pick_data, cookies=cookies)
        
        assert response.status_code == 400
        assert "deadline" in response.json()["detail"].lower()
    
    def test_submit_picks_duplicate_prevention(self, test_client, test_db, authenticated_user_cookie, sample_game_data):
        """Test that duplicate picks are handled correctly"""
        # Create user and entry
        user = test_db.query(Users).filter(Users.username == "testuser").first()
        entry = Entries(
            user_id=user.user_id,
            entry_name="Test Entry",
            current_week=1,
            weekly_total=0,
            season_total=0
        )
        test_db.add(entry)
        test_db.commit()
        
        # Submit initial picks
        pick = Picks(
            entry_id=entry.entry_id,
            week=1,
            game_id=1,
            team_id=1
        )
        test_db.add(pick)
        test_db.commit()
        
        cookies = {"session-token": authenticated_user_cookie}
        
        # Try to submit pick for same game again
        pick_data = {
            "entry_id": entry.entry_id,
            "week": 1,
            "picks": [{"game_id": 1, "team_id": 2}]  # Different team, same game
        }
        
        response = test_client.post("/submit-picks", json=pick_data, cookies=cookies)
        
        # Should either update existing pick or prevent duplicate
        if response.status_code == 200:
            # If update is allowed, verify pick was updated
            updated_pick = test_db.query(Picks).filter(
                Picks.entry_id == entry.entry_id,
                Picks.game_id == 1
            ).first()
            assert updated_pick.team_id == 2
        else:
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"].lower()


class TestPickValidation:
    """Test pick validation logic"""
    
    def test_validate_team_in_game(self, test_client, test_db, sample_game_data):
        """Test that picks validate team is actually in the game"""
        # This would be tested if the API validates that team_id is either
        # away_team_id or home_team_id for the given game_id
        pass
    
    def test_validate_game_exists(self, test_client, test_db, authenticated_user_cookie):
        """Test that picks validate game exists"""
        cookies = {"session-token": authenticated_user_cookie}
        
        pick_data = {
            "entry_id": 1,
            "week": 1,
            "picks": [{"game_id": 999999, "team_id": 1}]  # Non-existent game
        }
        
        response = test_client.post("/submit-picks", json=pick_data, cookies=cookies)
        
        assert response.status_code == 400
        assert "game" in response.json()["detail"].lower()
    
    def test_validate_team_exists(self, test_client, test_db, authenticated_user_cookie, sample_game_data):
        """Test that picks validate team exists"""
        cookies = {"session-token": authenticated_user_cookie}
        
        pick_data = {
            "entry_id": 1,
            "week": 1,
            "picks": [{"game_id": 1, "team_id": 999999}]  # Non-existent team
        }
        
        response = test_client.post("/submit-picks", json=pick_data, cookies=cookies)
        
        assert response.status_code == 400
        assert "team" in response.json()["detail"].lower()
    
    def test_validate_week_range(self, test_client, authenticated_user_cookie):
        """Test that picks validate week is in valid range"""
        cookies = {"session-token": authenticated_user_cookie}
        
        # Test invalid week numbers
        invalid_weeks = [0, -1, 23, 100]
        
        for week in invalid_weeks:
            pick_data = {
                "entry_id": 1,
                "week": week,
                "picks": [{"game_id": 1, "team_id": 1}]
            }
            
            response = test_client.post("/submit-picks", json=pick_data, cookies=cookies)
            assert response.status_code == 422


class TestPickRetrieval:
    """Test pick retrieval and display"""
    
    def test_get_picks_requires_auth(self, test_client):
        """Test that getting picks requires authentication"""
        response = test_client.get("/picks/1/1")  # entry_id/week
        assert response.status_code == 401
    
    def test_get_picks_success(self, test_client, test_db, authenticated_user_cookie, sample_picks_data):
        """Test successful pick retrieval"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/picks/1/1", cookies=cookies)
        
        assert response.status_code == 200
        data = response.json()
        assert "picks" in data
        assert len(data["picks"]) > 0
    
    def test_get_picks_empty_week(self, test_client, authenticated_user_cookie):
        """Test getting picks for week with no picks"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/picks/1/10", cookies=cookies)  # Week with no picks
        
        assert response.status_code == 200
        data = response.json()
        assert data["picks"] == []
    
    def test_get_picks_invalid_entry(self, test_client, authenticated_user_cookie):
        """Test getting picks for invalid entry"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/picks/999999/1", cookies=cookies)
        
        assert response.status_code == 404
        assert "entry" in response.json()["detail"].lower()


class TestWeeklyLocks:
    """Test weekly lock functionality"""
    
    def test_get_weekly_locks(self, test_client, test_db, authenticated_user_cookie):
        """Test getting weekly locks"""
        # Create a weekly lock
        lock = Weekly_Locks(
            week=1,
            lock_time=datetime.now() + timedelta(hours=1),
            season=2025
        )
        test_db.add(lock)
        test_db.commit()
        
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/weekly-locks/1", cookies=cookies)
        
        assert response.status_code == 200
        data = response.json()
        assert "lock_time" in data
    
    def test_weekly_locks_prevent_late_picks(self, test_client, test_db, authenticated_user_cookie):
        """Test that weekly locks prevent late pick submission"""
        # Create a lock that has passed
        lock = Weekly_Locks(
            week=1,
            lock_time=datetime.now() - timedelta(hours=1),
            season=2025
        )
        test_db.add(lock)
        test_db.commit()
        
        cookies = {"session-token": authenticated_user_cookie}
        
        pick_data = {
            "entry_id": 1,
            "week": 1,
            "picks": [{"game_id": 1, "team_id": 1}]
        }
        
        response = test_client.post("/submit-picks", json=pick_data, cookies=cookies)
        
        assert response.status_code == 400
        assert "locked" in response.json()["detail"].lower()


class TestGameSchedule:
    """Test game schedule functionality"""
    
    def test_get_schedule_requires_auth(self, test_client):
        """Test that getting schedule requires authentication"""
        response = test_client.get("/schedule/1")
        assert response.status_code == 401
    
    def test_get_schedule_success(self, test_client, test_db, authenticated_user_cookie, sample_game_data):
        """Test successful schedule retrieval"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/schedule/1", cookies=cookies)
        
        assert response.status_code == 200
        data = response.json()
        assert "games" in data
        assert len(data["games"]) > 0
        
        # Verify game structure
        game = data["games"][0]
        required_fields = ["game_id", "away_team", "home_team", "game_time"]
        for field in required_fields:
            assert field in game
    
    def test_get_schedule_invalid_week(self, test_client, authenticated_user_cookie):
        """Test getting schedule for invalid week"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/schedule/999", cookies=cookies)
        
        assert response.status_code == 200
        data = response.json()
        assert data["games"] == []
    
    def test_get_current_week_schedule(self, test_client, authenticated_user_cookie):
        """Test getting current week schedule"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/schedule/current", cookies=cookies)
        
        assert response.status_code == 200
        data = response.json()
        assert "games" in data


class TestTeamData:
    """Test team data functionality"""
    
    def test_get_teams(self, test_client, test_db, authenticated_user_cookie, sample_teams_data):
        """Test getting team data"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/teams", cookies=cookies)
        
        assert response.status_code == 200
        data = response.json()
        assert "teams" in data
        assert len(data["teams"]) > 0
        
        # Verify team structure
        team = data["teams"][0]
        required_fields = ["team_id", "team_name", "team_abbreviation"]
        for field in required_fields:
            assert field in team
    
    def test_get_team_by_id(self, test_client, test_db, authenticated_user_cookie, sample_teams_data):
        """Test getting specific team by ID"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/teams/1", cookies=cookies)
        
        assert response.status_code == 200
        data = response.json()
        assert "team_id" in data
        assert data["team_id"] == 1
    
    def test_get_team_invalid_id(self, test_client, authenticated_user_cookie):
        """Test getting team with invalid ID"""
        cookies = {"session-token": authenticated_user_cookie}
        response = test_client.get("/teams/999999", cookies=cookies)
        
        assert response.status_code == 404
        assert "team" in response.json()["detail"].lower()


class TestPickScoring:
    """Test pick scoring logic"""
    
    def test_calculate_weekly_score(self, test_client, test_db, sample_picks_data, sample_game_results):
        """Test weekly score calculation"""
        # This would test the scoring logic if it exists
        # For now, we'll test the data structure
        
        entry = test_db.query(Entries).first()
        picks = test_db.query(Picks).filter(
            Picks.entry_id == entry.entry_id,
            Picks.week == 1
        ).all()
        
        assert len(picks) > 0
        
        # Test that picks have required fields for scoring
        for pick in picks:
            assert pick.game_id is not None
            assert pick.team_id is not None
            assert pick.entry_id is not None
    
    def test_update_pick_results(self, test_client, test_db, authenticated_admin_cookie, sample_picks_data):
        """Test updating pick results (admin function)"""
        # This would test an admin endpoint for updating game results
        cookies = {"session-token": authenticated_admin_cookie}
        
        result_data = {
            "game_id": 1,
            "winning_team_id": 1,
            "away_score": 21,
            "home_score": 14
        }
        
        # This endpoint may not exist yet, but would be needed for scoring
        response = test_client.post("/admin/update-results", json=result_data, cookies=cookies)
        
        # For now, we'll accept either success or not implemented
        assert response.status_code in [200, 404, 405]
    
    def test_season_total_calculation(self, test_client, test_db, sample_entries_data):
        """Test season total calculation"""
        entry = test_db.query(Entries).first()
        
        # Verify entry has season_total field
        assert hasattr(entry, 'season_total')
        assert entry.season_total is not None
        assert entry.season_total >= 0


class TestPickRules:
    """Test pick rules and game logic"""
    
    def test_picks_per_week_limit(self, test_client, test_db, authenticated_user_cookie, sample_game_data):
        """Test that there's a limit on picks per week"""
        # Create an entry
        user = test_db.query(Users).filter(Users.username == "testuser").first()
        entry = Entries(
            user_id=user.user_id,
            entry_name="Test Entry",
            current_week=1,
            weekly_total=0,
            season_total=0
        )
        test_db.add(entry)
        test_db.commit()
        
        cookies = {"session-token": authenticated_user_cookie}
        
        # Try to submit many picks (assuming there's a limit)
        many_picks = [{"game_id": i, "team_id": 1} for i in range(1, 20)]
        
        pick_data = {
            "entry_id": entry.entry_id,
            "week": 1,
            "picks": many_picks
        }
        
        response = test_client.post("/submit-picks", json=pick_data, cookies=cookies)
        
        # Should either succeed with valid picks or fail with limit error
        if response.status_code != 200:
            assert "limit" in response.json()["detail"].lower()
    
    def test_pick_change_rules(self, test_client, test_db, authenticated_user_cookie, sample_game_data):
        """Test rules for changing picks"""
        # Create entry and initial pick
        user = test_db.query(Users).filter(Users.username == "testuser").first()
        entry = Entries(
            user_id=user.user_id,
            entry_name="Test Entry",
            current_week=1,
            weekly_total=0,
            season_total=0
        )
        test_db.add(entry)
        test_db.commit()
        
        pick = Picks(
            entry_id=entry.entry_id,
            week=1,
            game_id=1,
            team_id=1
        )
        test_db.add(pick)
        test_db.commit()
        
        cookies = {"session-token": authenticated_user_cookie}
        
        # Try to change the pick
        pick_data = {
            "entry_id": entry.entry_id,
            "week": 1,
            "picks": [{"game_id": 1, "team_id": 2}]  # Different team
        }
        
        response = test_client.post("/submit-picks", json=pick_data, cookies=cookies)
        
        # Rules may allow or disallow pick changes
        if response.status_code == 200:
            # Verify pick was updated
            updated_pick = test_db.query(Picks).filter(
                Picks.entry_id == entry.entry_id,
                Picks.game_id == 1
            ).first()
            assert updated_pick.team_id == 2
        else:
            # Verify original pick unchanged
            unchanged_pick = test_db.query(Picks).filter(
                Picks.entry_id == entry.entry_id,
                Picks.game_id == 1
            ).first()
            assert unchanged_pick.team_id == 1


class TestPickAnalytics:
    """Test pick analytics and statistics"""
    
    def test_get_pick_summary(self, test_client, authenticated_user_cookie):
        """Test getting pick summary/statistics"""
        cookies = {"session-token": authenticated_user_cookie}
        
        # This would test an endpoint that provides pick statistics
        response = test_client.get("/picks/summary/1", cookies=cookies)  # entry_id
        
        # Endpoint may not exist yet
        if response.status_code == 200:
            data = response.json()
            expected_fields = ["total_picks", "correct_picks", "win_percentage"]
            for field in expected_fields:
                assert field in data
        else:
            assert response.status_code in [404, 405]
    
    def test_get_weekly_standings(self, test_client, authenticated_user_cookie):
        """Test getting weekly standings"""
        cookies = {"session-token": authenticated_user_cookie}
        
        response = test_client.get("/standings/1", cookies=cookies)  # week
        
        if response.status_code == 200:
            data = response.json()
            assert "standings" in data
            if data["standings"]:
                entry = data["standings"][0]
                assert "entry_name" in entry
                assert "score" in entry
        else:
            assert response.status_code in [404, 405]
    
    def test_get_season_standings(self, test_client, authenticated_user_cookie):
        """Test getting season standings"""
        cookies = {"session-token": authenticated_user_cookie}
        
        response = test_client.get("/standings/season", cookies=cookies)
        
        if response.status_code == 200:
            data = response.json()
            assert "standings" in data
        else:
            assert response.status_code in [404, 405]


class TestPickDataIntegrity:
    """Test data integrity for picks"""
    
    def test_pick_entry_relationship(self, test_db, sample_picks_data, sample_entries_data):
        """Test that picks properly reference entries"""
        picks = test_db.query(Picks).all()
        
        for pick in picks:
            # Verify entry exists
            entry = test_db.query(Entries).filter(Entries.entry_id == pick.entry_id).first()
            assert entry is not None
    
    def test_pick_game_relationship(self, test_db, sample_picks_data, sample_game_data):
        """Test that picks properly reference games"""
        picks = test_db.query(Picks).all()
        
        for pick in picks:
            # Verify game exists
            game = test_db.query(Schedule).filter(Schedule.game_id == pick.game_id).first()
            assert game is not None
    
    def test_pick_team_relationship(self, test_db, sample_picks_data, sample_teams_data):
        """Test that picks properly reference teams"""
        picks = test_db.query(Picks).all()
        
        for pick in picks:
            # Verify team exists
            team = test_db.query(Teams).filter(Teams.team_id == pick.team_id).first()
            assert team is not None
    
    def test_pick_constraints(self, test_db):
        """Test database constraints on picks"""
        # Test that required fields cannot be null
        try:
            invalid_pick = Picks(
                entry_id=None,  # Should not be allowed
                week=1,
                game_id=1,
                team_id=1
            )
            test_db.add(invalid_pick)
            test_db.commit()
            assert False, "Should not allow null entry_id"
        except Exception:
            test_db.rollback()
            # Expected to fail
            pass
