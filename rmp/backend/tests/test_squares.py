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


def _grant_plan(db, user_id, plan="commissioner"):
    now = datetime(2026, 8, 1)
    order = models.BillingOrder(
        id=f"squares-order-{user_id}", user_id=user_id, season=2026,
        plan=plan, status="paid", created_at=now, updated_at=now,
    )
    entitlement = models.CommissionerEntitlement(
        id=f"squares-entitlement-{user_id}", user_id=user_id, season=2026,
        plan=plan, status="active", included_entries=100 if plan == "squares-plus" else 50, max_pools=1,
        unlimited_entries=False, source_order_id=order.id, activated_at=now, updated_at=now,
    )
    db.add_all([order, entitlement]); db.commit()
    return entitlement


def _grant_commish(db, user_id):
    return _grant_plan(db, user_id)


def test_squares_creation_requires_future_known_game(client, db_session):
    _, headers = _register(client, "squares-owner@example.com")
    missing = client.post("/pools/create", json={"name": "Missing Game", "pool_type": "squares"}, headers=headers)
    assert missing.status_code == 400
    _game(db_session, start=datetime.utcnow() - timedelta(minutes=1))
    started = client.post("/pools/create", json={"name": "Started Game", "pool_type": "squares", "squares_game_id": 9001}, headers=headers)
    assert started.status_code == 409


def test_free_plan_includes_one_board_and_25_self_service_blocks(client, db_session):
    owner, headers = _register(client, "free-squares-owner@example.com")
    _, member_headers = _register(client, "free-squares-member@example.com")
    _game(db_session)
    pool = _create(client, headers, name="Free Squares Board")
    assert client.post(f"/pools/{pool['id']}/join", json={}, headers=member_headers).status_code == 200
    board = client.get(f"/squares/{pool['id']}", headers=headers).json()
    assert board["plan"] == "free" and board["block_limit"] == 25
    assert board["permissions"]["can_admin_assign"] is False
    assert board["permissions"]["can_use_variable_pot"] is False

    db_session.add_all([
        models.SquareClaim(
            id=f"free-claim-{index}", pool_id=pool["id"], row_index=index // 10,
            column_index=index % 10, user_id=owner["id"], assigned_by=owner["id"],
            claimed_at=datetime.utcnow(),
        ) for index in range(25)
    ])
    db_session.commit()
    blocked = client.post(f"/squares/{pool['id']}/claims", json={"row_index": 2, "column_index": 5}, headers=member_headers)
    assert blocked.status_code == 409
    assert "Upgrade to Squares Plus" in blocked.json()["detail"]

    admin_assignment = client.post(f"/squares/{pool['id']}/claims", json={
        "row_index": 2, "column_index": 6,
        "user_id": db_session.query(models.User).filter_by(email="free-squares-member@example.com").one().id,
    }, headers=headers)
    assert admin_assignment.status_code == 403
    variable_pot = client.patch(f"/squares/{pool['id']}/payouts", json={
        "pot_mode": "per_square", "per_square_cents": 500, "total_pot_cents": None,
        "q1_percent": 25, "halftime_percent": 25, "q3_percent": 25, "final_percent": 25,
    }, headers=headers)
    assert variable_pot.status_code == 403
    assert client.post("/pools/create", json={
        "name": "Second Free Squares Board", "pool_type": "squares", "squares_game_id": 9001,
    }, headers=headers).status_code == 409


def test_squares_plus_opens_100_blocks_but_keeps_commish_controls_locked(client, db_session):
    owner, headers = _register(client, "squares-plus-owner@example.com")
    member, member_headers = _register(client, "squares-plus-member@example.com")
    _grant_plan(db_session, owner["id"], "squares-plus")
    _game(db_session)
    pool = _create(client, headers, name="Squares Plus Board")
    assert client.post(f"/pools/{pool['id']}/join", json={}, headers=member_headers).status_code == 200
    board = client.get(f"/squares/{pool['id']}", headers=headers).json()

    assert board["plan"] == "squares-plus"
    assert board["block_limit"] == 100
    assert board["permissions"]["can_claim"] is True
    assert board["permissions"]["can_admin_assign"] is False
    assert board["permissions"]["can_use_variable_pot"] is False
    assignment = client.post(f"/squares/{pool['id']}/claims", json={
        "row_index": 0, "column_index": 0, "user_id": member["id"],
    }, headers=headers)
    assert assignment.status_code == 403
    variable_pot = client.patch(f"/squares/{pool['id']}/payouts", json={
        "pot_mode": "per_square", "per_square_cents": 500, "total_pot_cents": None,
        "q1_percent": 25, "halftime_percent": 25, "q3_percent": 25, "final_percent": 25,
    }, headers=headers)
    assert variable_pot.status_code == 403


def test_claim_collision_release_and_admin_lock(client, db_session):
    owner, headers = _register(client, "board-owner@example.com")
    _game(db_session)
    pool = _create(client, headers)
    first = client.post(f"/squares/{pool['id']}/claims", json={"row_index": 2, "column_index": 7}, headers=headers)
    assert first.status_code == 201
    assert first.json()["block_number"] == 28
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


def test_member_sees_reservations_and_pot_but_cannot_administer_board(client, db_session):
    owner, owner_headers = _register(client, "visible-board-owner@example.com")
    _, member_headers = _register(client, "visible-board-member@example.com")
    _game(db_session)
    pool = _create(client, owner_headers)
    assert client.post(f"/pools/{pool['id']}/join", json={}, headers=member_headers).status_code == 200
    configured = client.patch(f"/squares/{pool['id']}/payouts", json={
        "total_pot_cents": 12345, "q1_percent": 25, "halftime_percent": 25,
        "q3_percent": 25, "final_percent": 25,
    }, headers=owner_headers)
    assert configured.status_code == 200
    claimed = client.post(f"/squares/{pool['id']}/claims", json={"row_index": 4, "column_index": 6}, headers=owner_headers)
    assert claimed.status_code == 201

    visible = client.get(f"/squares/{pool['id']}", headers=member_headers)
    assert visible.status_code == 200
    body = visible.json()
    assert body["total_pot_cents"] == 12345
    assert body["permissions"]["is_admin"] is False
    assert body["members"] == []
    assert body["claims"][0]["user_email"] == owner["email"]
    assert body["claims"][0]["block_number"] == 47
    assert body["home_digits"] is None and body["away_digits"] is None

    denied_payout = client.patch(f"/squares/{pool['id']}/payouts", json={
        "total_pot_cents": 99999, "q1_percent": 25, "halftime_percent": 25,
        "q3_percent": 25, "final_percent": 25,
    }, headers=member_headers)
    assert denied_payout.status_code == 403
    assert client.post(f"/squares/{pool['id']}/lock", headers=member_headers).status_code == 403
    assigned_to_owner = client.post(f"/squares/{pool['id']}/claims", json={
        "row_index": 0, "column_index": 0, "user_id": owner["id"],
    }, headers=member_headers)
    assert assigned_to_owner.status_code == 403


def test_per_square_pot_tracks_authoritative_reservation_count(client, db_session):
    owner, headers = _register(client, "variable-pot-owner@example.com")
    _grant_commish(db_session, owner["id"])
    _game(db_session)
    pool = _create(client, headers)
    missing_rate = client.patch(f"/squares/{pool['id']}/payouts", json={
        "pot_mode": "per_square", "total_pot_cents": None, "per_square_cents": None,
        "q1_percent": 25, "halftime_percent": 25, "q3_percent": 25, "final_percent": 25,
    }, headers=headers)
    assert missing_rate.status_code == 400

    configured = client.patch(f"/squares/{pool['id']}/payouts", json={
        "pot_mode": "per_square", "total_pot_cents": None, "per_square_cents": 500,
        "q1_percent": 25, "halftime_percent": 25, "q3_percent": 25, "final_percent": 25,
    }, headers=headers)
    assert configured.status_code == 200
    assert configured.json()["pot_mode"] == "per_square"
    assert configured.json()["plan"] == "commissioner"
    assert configured.json()["block_limit"] == 100
    assert configured.json()["per_square_cents"] == 500
    assert configured.json()["total_pot_cents"] == 0

    first = client.post(f"/squares/{pool['id']}/claims", json={"row_index": 0, "column_index": 0}, headers=headers)
    second = client.post(f"/squares/{pool['id']}/claims", json={"row_index": 0, "column_index": 1}, headers=headers)
    assert first.status_code == 201 and second.status_code == 201
    assert client.get(f"/squares/{pool['id']}", headers=headers).json()["total_pot_cents"] == 1000

    assert client.delete(f"/squares/{pool['id']}/claims/{second.json()['id']}", headers=headers).status_code == 204
    assert client.get(f"/squares/{pool['id']}", headers=headers).json()["total_pot_cents"] == 500


def test_board_randomizes_score_digits_automatically_at_kickoff(client, db_session):
    _, headers = _register(client, "automatic-lock-owner@example.com")
    game = _game(db_session)
    pool = _create(client, headers)
    before = client.get(f"/squares/{pool['id']}", headers=headers).json()
    assert before["locked"] is False
    assert before["home_digits"] is None and before["away_digits"] is None

    game.start_time = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    after = client.get(f"/squares/{pool['id']}", headers=headers)
    assert after.status_code == 200
    body = after.json()
    assert body["locked"] is True
    assert sorted(body["home_digits"]) == list(range(10))
    assert sorted(body["away_digits"]) == list(range(10))


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
    board.pot_mode = "per_square"
    board.total_pot_cents = None
    board.per_square_cents = 20000
    apply_game_results(db_session, [result]); db_session.commit()
    payout = db_session.query(models.SquarePayout).one()
    assert payout.winner_user_id == owner.id and payout.amount_cents == 5000


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
