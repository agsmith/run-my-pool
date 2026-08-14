import json
from datetime import datetime, timedelta

import models
from services.nfl_results import NflGameResult, parse_scoreboard
from services.scoring import apply_game_results


def _register(client, email):
    password = "Pass1234!"
    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return response.json(), {"Authorization": f"Bearer {login.json()['access_token']}"}


def _game(db, game_id=9001, start=None):
    home = models.Team(id=901, name="Home Team", abbrv="HOM")
    away = models.Team(id=902, name="Away Team", abbrv="AWY")
    game = models.Schedule(
        game_id=game_id, season=2026, week_num=1,
        home_team_id=home.id, away_team_id=away.id,
        start_time=start or datetime.utcnow() + timedelta(days=7), status="scheduled",
    )
    db.add_all([home, away, game]); db.commit()
    return game


def _create(client, headers, game_id=9001, name="Sunday Squares"):
    response = client.post("/pools/create", json={
        "name": name, "pool_type": "squares", "squares_game_id": game_id,
    }, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_squares_creation_requires_future_known_game(client, db_session):
    _, headers = _register(client, "squares-owner@example.com")
    missing = client.post("/pools/create", json={"name": "Missing Game", "pool_type": "squares"}, headers=headers)
    assert missing.status_code == 400
    _game(db_session, start=datetime.utcnow() - timedelta(minutes=1))
    started = client.post("/pools/create", json={"name": "Started Game", "pool_type": "squares", "squares_game_id": 9001}, headers=headers)
    assert started.status_code == 409


def test_claim_collision_release_and_admin_lock(client, db_session):
    owner, headers = _register(client, "board-owner@example.com")
    _game(db_session)
    pool = _create(client, headers)
    first = client.post(f"/squares/{pool['id']}/claims", json={"row_index": 2, "column_index": 7}, headers=headers)
    assert first.status_code == 201
    collision = client.post(f"/squares/{pool['id']}/claims", json={"row_index": 2, "column_index": 7}, headers=headers)
    assert collision.status_code == 409
    released = client.delete(f"/squares/{pool['id']}/claims/{first.json()['id']}", headers=headers)
    assert released.status_code == 204
    client.post(f"/squares/{pool['id']}/claims", json={"row_index": 2, "column_index": 7}, headers=headers)
    locked = client.post(f"/squares/{pool['id']}/lock", headers=headers)
    assert locked.status_code == 200
    body = locked.json()
    assert sorted(body["home_digits"]) == list(range(10))
    assert sorted(body["away_digits"]) == list(range(10))
    assert client.post(f"/squares/{pool['id']}/lock", headers=headers).status_code == 409
    assert client.post(f"/squares/{pool['id']}/claims", json={"row_index": 1, "column_index": 1}, headers=headers).status_code == 409


def test_nonmember_cannot_read_board(client, db_session):
    _, owner_headers = _register(client, "private-board-owner@example.com")
    _, outsider_headers = _register(client, "squares-outsider@example.com")
    _game(db_session)
    pool = _create(client, owner_headers)
    assert client.get(f"/squares/{pool['id']}", headers=outsider_headers).status_code == 403


def test_quarter_payouts_are_idempotent_and_correctable(db_session):
    owner = models.User(id="owner", email="owner@squares.test", hashed_password="x", is_active=True)
    _game(db_session)
    pool = models.Pool(id="square-pool", name="Scored Squares", pool_type="squares", squares_game_id=9001, owner_id=owner.id, created_at=datetime.utcnow())
    board = models.SquareBoard(
        pool_id=pool.id, home_digits=json.dumps(list(range(10))), away_digits=json.dumps(list(range(10))),
        total_pot_cents=10000, locked_at=datetime.utcnow(), created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    claim = models.SquareClaim(id="claim", pool_id=pool.id, row_index=7, column_index=3, user_id=owner.id, assigned_by=owner.id, claimed_at=datetime.utcnow())
    db_session.add_all([owner, pool, board, claim]); db_session.commit()
    result = NflGameResult(9001, 2026, 1, "in_progress", "HOM", "AWY", 7, 3, home_q1_score=7, away_q1_score=3, completed_period=1)
    apply_game_results(db_session, [result]); db_session.commit()
    payout = db_session.query(models.SquarePayout).one()
    assert payout.checkpoint == "q1" and payout.winner_user_id == owner.id and payout.amount_cents == 2500
    corrected = NflGameResult(9001, 2026, 1, "in_progress", "HOM", "AWY", 6, 3, home_q1_score=6, away_q1_score=3, completed_period=1)
    apply_game_results(db_session, [corrected]); db_session.commit()
    payouts = db_session.query(models.SquarePayout).all()
    assert len(payouts) == 1 and payouts[0].winning_row == 6 and payouts[0].winner_user_id is None


def test_espn_linescores_are_converted_to_cumulative_checkpoint_scores():
    payload = {"events": [{
        "id": "9001", "status": {"period": 3, "type": {"name": "STATUS_END_PERIOD"}},
        "competitions": [{"competitors": [
            {"homeAway": "home", "score": "17", "team": {"abbreviation": "HOM"}, "linescores": [{"period": 1, "value": 7}, {"period": 2, "value": 3}, {"period": 3, "value": 7}]},
            {"homeAway": "away", "score": "13", "team": {"abbreviation": "AWY"}, "linescores": [{"period": 1, "value": 3}, {"period": 2, "value": 7}, {"period": 3, "value": 3}]},
        ]}],
    }]}
    result = parse_scoreboard(payload, season=2026, week=1)[0]
    assert result.completed_period == 3
    assert (result.home_q1_score, result.home_half_score, result.home_q3_score) == (7, 10, 17)
    assert (result.away_q1_score, result.away_half_score, result.away_q3_score) == (3, 10, 13)
