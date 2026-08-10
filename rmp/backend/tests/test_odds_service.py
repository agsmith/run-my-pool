from datetime import datetime
from types import SimpleNamespace

import models
from odds_service import fetch_game_line, freeze_week_lines


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "pickcenter": [{
                "provider": {"name": "DraftKings"},
                "details": "HOME -6.5",
                "spread": -6.5,
                "homeTeamOdds": {"favorite": True},
                "awayTeamOdds": {"favorite": False},
            }]
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
    pool = models.Pool(
        id="odds-pool", name="Odds", owner_id="owner", is_private=False
    )
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
        lambda games: {7001: {
            "game_id": 7001, "favorite_team_id": 81, "spread": 6.5,
            "details": "HOME -6.5", "provider": "DraftKings",
        }},
    )

    freeze_week_lines(db_session, pool.id, 1, [game], datetime(2026, 9, 6, 16))
    db_session.commit()
    snapshot = db_session.query(models.PoolGameLine).one()
    assert snapshot.spread == 6.5
    assert snapshot.favorite_team_id == 81
    assert snapshot.captured_at == datetime(2026, 9, 6, 16)
