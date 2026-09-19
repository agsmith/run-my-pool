from datetime import datetime, timedelta

import models
import prepare_app_review_account as review_setup


def _seed_schedule(db_session):
    teams = []
    for index in range(8):
        team = models.Team(
            id=9100 + index,
            name=f"Review Team {index + 1}",
            abbrv=f"R{index + 1}",
            logo=None,
        )
        db_session.add(team)
        teams.append(team)
    db_session.flush()
    games = []
    for index in range(4):
        game = models.Schedule(
            game_id=991000 + index,
            season=2026,
            week_num=1,
            home_team_id=teams[index * 2].id,
            away_team_id=teams[index * 2 + 1].id,
            start_time=datetime.utcnow() - timedelta(days=8, hours=index),
            status="final",
            home_score=24 + index,
            away_score=17 + index,
            winning_team_id=teams[index * 2].id,
        )
        db_session.add(game)
        games.append(game)
    db_session.commit()
    return games


def test_review_setup_is_idempotent_and_keeps_login_a_plain_member(
    db_session, monkeypatch
):
    games = _seed_schedule(db_session)
    monkeypatch.setattr(review_setup, "current_season_week", lambda db, now: 1)
    monkeypatch.setattr(review_setup, "current_season_games", lambda db, week: games)

    first = review_setup.seed_review_content(db_session, "ReviewPassword123")
    second = review_setup.seed_review_content(db_session, "ReviewPassword123")

    assert first["email"] == review_setup.REVIEW_EMAIL
    assert second["active"] is True
    assert second["email_verified"] is True
    assert second["role"] == "USER"
    assert second["pool_admin_grants"] == 0
    assert {pool["type"] for pool in second["pools"]} == {
        "survivor",
        "pickem",
        "squares",
    }
    assert all(pool["messages"] == 3 for pool in second["pools"])
    assert sum(pool["square_claims"] for pool in second["pools"]) == 4

    reviewer = db_session.query(models.User).filter_by(
        email=review_setup.REVIEW_EMAIL
    ).one()
    assert review_setup.PASSWORDS.verify(
        "ReviewPassword123", reviewer.hashed_password
    )
    assert db_session.query(models.Pool).filter(
        models.Pool.name.like("App Review % Demo")
    ).count() == 3
    assert db_session.query(models.MessageBoard).filter(
        models.MessageBoard.pool_id.in_(pool["id"] for pool in second["pools"])
    ).count() == 9
    assert db_session.query(models.AuditLog).filter_by(
        action="ADMIN_AUTO_PICK"
    ).count() == 1
