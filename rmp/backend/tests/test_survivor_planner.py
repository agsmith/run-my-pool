import uuid
from datetime import datetime

from models import Entry, Pick, Pool, PoolMember, Schedule, SurvivorEntryPlan, Team, User


def _register(client, email):
    password = "SecurePass1!"
    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 200
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _seed(db, owner_id, member_id, outsider_id):
    pool = Pool(id="planner-pool", name=f"Planner {uuid.uuid4()}", pool_type="survivor", owner_id=owner_id, survivor_objective="win")
    db.add(pool)
    db.add(PoolMember(pool_id=pool.id, user_id=member_id, joined_at=datetime.utcnow()))
    entries = [
        Entry(id="member-entry", user_id=member_id, pool_id=pool.id, name="Mine", alive=True),
        Entry(id="owner-entry", user_id=owner_id, pool_id=pool.id, name="Owner secret", alive=True),
    ]
    db.add_all(entries)
    teams = [Team(id=901, name="Buffalo", abbrv="BUF"), Team(id=902, name="Miami", abbrv="MIA"), Team(id=903, name="Kansas City", abbrv="KC"), Team(id=904, name="Denver", abbrv="DEN")]
    db.add_all(teams)
    db.add_all([
        Schedule(game_id=9901, season=2026, week_num=1, home_team_id=901, away_team_id=902, start_time=datetime(2026, 9, 10, 20)),
        Schedule(game_id=9902, season=2026, week_num=2, home_team_id=903, away_team_id=904, start_time=datetime(2026, 9, 17, 20)),
    ])
    db.commit()
    return pool


def test_planner_is_private_and_admin_roles_do_not_bypass_ownership(client, db_session):
    member_token = _register(client, "planner-member@example.com")
    owner_token = _register(client, "planner-owner@example.com")
    outsider_token = _register(client, "planner-outsider@example.com")
    users = {user.email: user for user in db_session.query(User).all()}
    _seed(db_session, users["planner-owner@example.com"].id, users["planner-member@example.com"].id, users["planner-outsider@example.com"].id)
    db_session.add(SurvivorEntryPlan(id="owner-plan", entry_id="owner-entry", week_num=2, team_id=903, created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
    db_session.commit()

    response = client.get("/survivor-planner/pools/planner-pool", headers={"Authorization": f"Bearer {member_token}"})
    assert response.status_code == 200
    assert [entry["id"] for entry in response.json()["entries"]] == ["member-entry"]
    assert "owner-plan" not in response.text

    # Owning the pool does not grant access to a member's private entry plan.
    response = client.put("/survivor-planner/entries/member-entry/weeks/2", json={"team": "KC"}, headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 404
    response = client.get("/survivor-planner/pools/planner-pool", headers={"Authorization": f"Bearer {outsider_token}"})
    assert response.status_code == 403


def test_plan_validation_duplicate_prevention_and_clear(client, db_session):
    member_token = _register(client, "planner-save@example.com")
    owner_token = _register(client, "planner-save-owner@example.com")
    outsider_token = _register(client, "planner-save-out@example.com")
    users = {user.email: user for user in db_session.query(User).all()}
    _seed(db_session, users["planner-save-owner@example.com"].id, users["planner-save@example.com"].id, users["planner-save-out@example.com"].id)
    headers = {"Authorization": f"Bearer {member_token}"}

    response = client.put("/survivor-planner/entries/member-entry/weeks/2", json={"team": "kc", "unexpected": True}, headers=headers)
    assert response.status_code == 422
    response = client.put("/survivor-planner/entries/member-entry/weeks/2", json={"team": "BUF"}, headers=headers)
    assert response.status_code == 400  # BUF is not on the Week 2 slate.
    response = client.put("/survivor-planner/entries/member-entry/weeks/2", json={"team": "KC"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["team"] == "KC"
    response = client.put("/survivor-planner/entries/member-entry/weeks/3", json={"team": "KC"}, headers=headers)
    assert response.status_code in (400, 409)
    response = client.delete("/survivor-planner/entries/member-entry/weeks/2", headers=headers)
    assert response.status_code == 200
    assert db_session.query(SurvivorEntryPlan).count() == 0


def test_planner_rejects_eliminated_entry_and_non_survivor_pool(client, db_session):
    token = _register(client, "planner-dead@example.com")
    owner_token = _register(client, "planner-dead-owner@example.com")
    out_token = _register(client, "planner-dead-out@example.com")
    users = {user.email: user for user in db_session.query(User).all()}
    _seed(db_session, users["planner-dead-owner@example.com"].id, users["planner-dead@example.com"].id, users["planner-dead-out@example.com"].id)
    db_session.query(Entry).filter(Entry.id == "member-entry").update({"alive": False})
    db_session.commit()
    response = client.put("/survivor-planner/entries/member-entry/weeks/2", json={"team": "KC"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

    pool = db_session.query(Pool).filter(Pool.id == "planner-pool").first()
    pool.pool_type = "pickem"
    db_session.commit()
    response = client.get("/survivor-planner/pools/planner-pool", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400


def test_current_plan_requires_explicit_promotion_through_official_pick_rules(client, db_session):
    token = _register(client, "planner-promote@example.com")
    _register(client, "planner-promote-owner@example.com")
    _register(client, "planner-promote-out@example.com")
    users = {user.email: user for user in db_session.query(User).all()}
    _seed(db_session, users["planner-promote-owner@example.com"].id, users["planner-promote@example.com"].id, users["planner-promote-out@example.com"].id)
    headers = {"Authorization": f"Bearer {token}"}

    saved = client.put("/survivor-planner/entries/member-entry/weeks/1", json={"team": "BUF"}, headers=headers)
    assert saved.status_code == 200
    assert db_session.query(Pick).count() == 0

    promoted = client.post("/survivor-planner/entries/member-entry/weeks/1/make-official", headers=headers)
    assert promoted.status_code == 200
    pick = db_session.query(Pick).one()
    assert (pick.entry_id, pick.week, pick.team) == ("member-entry", 1, "BUF")
    assert db_session.query(SurvivorEntryPlan).count() == 0

    # A future plan cannot be promoted early, even by its owner.
    saved = client.put("/survivor-planner/entries/member-entry/weeks/2", json={"team": "KC"}, headers=headers)
    assert saved.status_code == 200
    early = client.post("/survivor-planner/entries/member-entry/weeks/2/make-official", headers=headers)
    assert early.status_code == 400
