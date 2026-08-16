from datetime import datetime
from types import SimpleNamespace

import httpx
import models
from odds_service import fetch_game_line, freeze_week_lines


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "pickcenter": [
                {
                    "provider": {"name": "DraftKings"},
                    "details": "HOME -6.5",
                    "spread": -6.5,
                    "homeTeamOdds": {"favorite": True},
                    "awayTeamOdds": {"favorite": False},
                }
            ]
        }


class FakeClient:
    def get(self, url, params):
        assert params["event"] == 7001
        return FakeResponse()


def test_fetch_game_line_normalizes_favorite_and_spread():
    game = SimpleNamespace(game_id=7001, home_team_id=1, away_team_id=2)
    line = fetch_game_line(game, client=FakeClient())
    assert line["favorite_team_id"] == 1
    assert line["spread"] == 6.5
    assert line["details"] == "HOME -6.5"
    assert line["provider"] == "DraftKings"


def test_freeze_week_lines_persists_pool_snapshot(db_session, monkeypatch):
    pool = models.Pool(id="odds-pool", name="Odds", owner_id="owner", is_private=False)
    owner = models.User(
        id="owner", email="odds-owner@example.com", hashed_password="x", is_active=True
    )
    home = models.Team(id=81, name="Home", abbrv="HOME")
    away = models.Team(id=82, name="Away", abbrv="AWAY")
    game = models.Schedule(
        game_id=7001,
        week_num=1,
        home_team_id=81,
        away_team_id=82,
        start_time=datetime(2026, 9, 10),
    )
    db_session.add_all([owner, pool, home, away, game])
    db_session.commit()
    monkeypatch.setattr(
        "odds_service.fetch_week_lines",
        lambda games: {
            7001: {
                "game_id": 7001,
                "favorite_team_id": 81,
                "spread": 6.5,
                "details": "HOME -6.5",
                "provider": "DraftKings",
            }
        },
    )

    freeze_week_lines(db_session, pool.id, 1, [game], datetime(2026, 9, 6, 16))
    db_session.commit()
    snapshot = db_session.query(models.PoolGameLine).one()
    assert snapshot.spread == 6.5
    assert snapshot.favorite_team_id == 81
    assert snapshot.captured_at == datetime(2026, 9, 6, 16)


# ---------------------------------------------------------------------------
# Additional tests from rmp-backend-odds-service stub
# ---------------------------------------------------------------------------


class ErrorResponse:
    def raise_for_status(self):
        raise httpx.HTTPStatusError("ESPN API error", request=None, response=None)

    def json(self):
        return {}


class ErrorClient:
    def get(self, url, params):
        return ErrorResponse()


class EmptyClient:
    def get(self, url, params):
        response = FakeResponse()
        # Simulate no pickcenter data (e.g., pre-season game)
        response.json = lambda: {"pickcenter": []}
        response.raise_for_status = lambda: None
        return response


class MalformedJsonClient:
    def get(self, url, params):
        class BadResp:
            def raise_for_status(self):
                pass

            def json(self):
                raise ValueError("Not JSON")

        return BadResp()


def test_fetch_game_line_returns_none_on_http_error():
    """fetch_game_line returns None gracefully when the ESPN API call fails."""
    game = SimpleNamespace(game_id=7002, home_team_id=1, away_team_id=2)
    result = fetch_game_line(game, client=ErrorClient())
    assert result is None


def test_fetch_game_line_returns_none_when_no_pickcenter():
    """fetch_game_line returns None when no odds data is available (e.g. pre-season)."""
    game = SimpleNamespace(game_id=7003, home_team_id=1, away_team_id=2)
    result = fetch_game_line(game, client=EmptyClient())
    assert result is None


def test_fetch_game_line_returns_none_on_malformed_json():
    """fetch_game_line returns None when the ESPN API returns non-JSON."""
    game = SimpleNamespace(game_id=7004, home_team_id=1, away_team_id=2)
    result = fetch_game_line(game, client=MalformedJsonClient())
    assert result is None


def test_fetch_game_line_away_favorite():
    """fetch_game_line correctly identifies away team as favorite."""

    class AwayFavoriteResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "pickcenter": [
                    {
                        "provider": {"name": "ESPN BET"},
                        "details": "AWAY -3.0",
                        "spread": -3.0,
                        "homeTeamOdds": {"favorite": False},
                        "awayTeamOdds": {"favorite": True},
                    }
                ]
            }

    class AwayFavoriteClient:
        def get(self, url, params):
            return AwayFavoriteResponse()

    game = SimpleNamespace(game_id=7005, home_team_id=10, away_team_id=20)
    line = fetch_game_line(game, client=AwayFavoriteClient())
    assert line is not None
    assert line["favorite_team_id"] == 20
