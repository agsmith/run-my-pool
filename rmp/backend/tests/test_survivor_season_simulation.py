"""Deterministic, production-path Survivor season simulation at realistic scale."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import uuid

import pytest

import models
from services.nfl_results import NflGameResult
from services.scoring import apply_game_results
from weekly_locks import lock_pool_week, pool_week_lock_time

SEASON = 2026
MEMBER_COUNT = 200
WEEK_COUNT = 18
TEAM_COUNT = 32


def _register(client, email):
    password = "Pass1234!"
    response = client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _week_games(db, week):
    return (
        db.query(models.Schedule)
        .filter(
            models.Schedule.season == SEASON,
            models.Schedule.week_num == week,
        )
        .order_by(models.Schedule.game_id)
        .all()
    )


def _winner_and_loser_ids(games, week):
    winners = []
    losers = []
    for index, game in enumerate(games):
        home_wins = (index + week) % 2 == 0
        winners.append(game.home_team_id if home_wins else game.away_team_id)
        losers.append(game.away_team_id if home_wins else game.home_team_id)
    return winners, losers


def _result(game, week, *, status="final", tie=False):
    home_wins = ((game.game_id - week * 1000) + week) % 2 == 0
    if tie:
        home_score = away_score = 20
    elif home_wins:
        home_score, away_score = 27, 17
    else:
        home_score, away_score = 17, 27
    return NflGameResult(
        game_id=game.game_id,
        season=SEASON,
        week=week,
        status=status,
        home_abbreviation=game.home_team.abbrv,
        away_abbreviation=game.away_team.abbrv,
        home_score=home_score,
        away_score=away_score,
        completed_period=4 if status == "final" else 2,
        provider_updated_at=game.start_time + timedelta(hours=2),
    )


def _choose_unused(candidates, used, offset):
    for step in range(len(candidates)):
        candidate = candidates[(offset + step) % len(candidates)]
        if candidate not in used:
            return candidate
    raise AssertionError("The deterministic season exhausted eligible teams")


def _no_frozen_lines(db, pool_id, week, games, captured_at=None):
    return []


@pytest.mark.season
@pytest.mark.slow
def test_200_member_survivor_pool_completes_full_season(client, db_session):
    """Run 200 members and 1,284 entries through all 18 Survivor weeks."""
    owner_token = _register(client, "season.sim.owner@example.com")
    registration_deadline = datetime(2026, 9, 5, 16, tzinfo=timezone.utc)
    response = client.post(
        "/pools/create",
        json={
            "name": "Deterministic 200 Member Season",
            "description": "Automated full-season Survivor test",
            "pool_type": "survivor",
            "is_private": False,
            "lock_day_of_week": 6,
            "lock_time_of_day": "13:00",
            "lock_timezone": "America/New_York",
            "join_lock_time": registration_deadline.isoformat(),
        },
        headers=_headers(owner_token),
    )
    assert response.status_code == 200, response.text
    pool_id = response.json()["id"]
    pool = db_session.get(models.Pool, pool_id)
    owner = (
        db_session.query(models.User)
        .filter_by(email="season.sim.owner@example.com")
        .one()
    )
    paid_at = registration_deadline.replace(tzinfo=None) - timedelta(days=14)
    order = models.BillingOrder(
        id="season-simulation-order",
        user_id=owner.id,
        plan="club-unlimited",
        season=SEASON,
        status="paid",
        created_at=paid_at,
        updated_at=paid_at,
        paid_at=paid_at,
    )
    entitlement = models.CommissionerEntitlement(
        id="season-simulation-entitlement",
        user_id=owner.id,
        season=SEASON,
        plan="club-unlimited",
        status="active",
        included_entries=None,
        max_pools=None,
        unlimited_entries=True,
        source_order_id=order.id,
        activated_at=paid_at,
        updated_at=paid_at,
    )
    db_session.add_all([order, entitlement])
    pool.billing_entitlement_id = entitlement.id
    pool.billing_season = SEASON

    teams = [
        models.Team(
            id=10_000 + index,
            name=f"Season Team {index:02d}",
            abbrv=f"S{index:02d}",
        )
        for index in range(TEAM_COUNT)
    ]
    db_session.add_all(teams)
    base_kickoff = datetime(2026, 9, 6, 17)
    games = []
    for week in range(1, WEEK_COUNT + 1):
        kickoff = base_kickoff + timedelta(weeks=week - 1)
        for game_index in range(TEAM_COUNT // 2):
            games.append(
                models.Schedule(
                    game_id=week * 1000 + game_index,
                    season=SEASON,
                    week_num=week,
                    home_team_id=teams[game_index * 2].id,
                    away_team_id=teams[game_index * 2 + 1].id,
                    start_time=kickoff + timedelta(minutes=game_index),
                    status="scheduled",
                )
            )
    db_session.add_all(games)

    members = []
    memberships = []
    entries = []
    entry_count_by_user = {}
    joined_at = registration_deadline.replace(tzinfo=None) - timedelta(days=7)
    for user_index in range(MEMBER_COUNT):
        user = models.User(
            id=f"season-member-{user_index:03d}",
            email=f"season.member.{user_index:03d}@example.com",
            hashed_password=owner.hashed_password,
            is_active=True,
            email_verified=True,
            created_at=joined_at,
        )
        members.append(user)
        memberships.append(
            models.PoolMember(
                pool_id=pool_id,
                user_id=user.id,
                joined_at=joined_at,
            )
        )
        entry_count = user_index % 12 + 1
        entry_count_by_user[user.id] = entry_count
        for entry_index in range(entry_count):
            entries.append(
                models.Entry(
                    id=f"season-entry-{user_index:03d}-{entry_index:02d}",
                    user_id=user.id,
                    pool_id=pool_id,
                    name=f"Season Entry {user_index:03d}-{entry_index + 1}",
                    alive=True,
                    created_at=joined_at,
                    updated_at=joined_at,
                )
            )
    db_session.add_all(members + memberships + entries)
    db_session.commit()

    # The creator is enrolled automatically; the simulated population adds
    # exactly 200 playing members beyond that administrative owner account.
    assert db_session.query(models.PoolMember).filter_by(pool_id=pool_id).count() == 201
    assert len(entries) == sum(user_index % 12 + 1 for user_index in range(200))
    assert set(entry_count_by_user.values()) == set(range(1, 13))
    assert min(entry_count_by_user.values()) == 1
    assert max(entry_count_by_user.values()) == 12

    # Advance beyond registration lock and prove both joining and entry creation
    # fail closed using server time and the real API authorization path.
    pool.join_lock_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=1
    )
    db_session.commit()
    late_token = _register(client, "season.sim.late@example.com")
    late_join = client.post(
        f"/pools/{pool_id}/join", json={}, headers=_headers(late_token)
    )
    assert late_join.status_code == 423
    late_entry = client.post(
        "/entries/create",
        json={"pool_id": pool_id, "name": "Too Late"},
        headers=_headers(owner_token),
    )
    assert late_entry.status_code == 423
    assert db_session.query(models.PoolMember).filter_by(pool_id=pool_id).count() == 201

    team_by_id = {team.id: team for team in teams}
    alive_counts = [len(entries)]
    auto_pick_ids = []
    correction_checked = False
    tie_checked = False

    for week in range(1, WEEK_COUNT + 1):
        week_games = _week_games(db_session, week)
        assert len(week_games) == 16
        winners, losers = _winner_and_loser_ids(week_games, week)
        alive_entries = (
            db_session.query(models.Entry)
            .filter(
                models.Entry.pool_id == pool_id,
                models.Entry.alive.is_(True),
            )
            .order_by(models.Entry.id)
            .all()
        )
        assert alive_entries, f"No entries remained to exercise week {week}"
        alive_ids = [entry.id for entry in alive_entries]
        used_by_entry = defaultdict(set)
        for entry_id, team_id in (
            db_session.query(models.Pick.entry_id, models.Pick.team_id)
            .filter(models.Pick.entry_id.in_(alive_ids))
            .all()
        ):
            used_by_entry[entry_id].add(team_id)

        # Exactly one surviving entry intentionally misses each deadline so the
        # production auto-pick path is exercised every week.
        missing_entry_id = alive_entries[week % len(alive_entries)].id
        picks = []
        for entry_index, entry in enumerate(alive_entries):
            if entry.id == missing_entry_id:
                continue
            should_lose = (entry_index + week) % 5 == 0
            candidates = losers if should_lose else winners
            team_id = _choose_unused(
                candidates,
                used_by_entry[entry.id],
                entry_index + week,
            )
            picks.append(
                models.Pick(
                    id=str(uuid.uuid4()),
                    entry_id=entry.id,
                    week=week,
                    team=team_by_id[team_id].abbrv,
                    team_id=team_id,
                    locked=False,
                    result=None,
                    created_at=week_games[0].start_time - timedelta(hours=2),
                    updated_at=week_games[0].start_time - timedelta(hours=2),
                )
            )
        db_session.bulk_save_objects(picks)
        db_session.commit()

        deadline = pool_week_lock_time(pool, week_games)
        assert deadline is not None
        lock_time = deadline + timedelta(seconds=1)
        auto_count = lock_pool_week(
            db_session,
            pool,
            week,
            owner.id,
            now=lock_time,
            games_provider=lambda db, requested_week: _week_games(db, requested_week),
            line_freezer=_no_frozen_lines,
        )
        assert auto_count == 1
        assert (
            lock_pool_week(
                db_session,
                pool,
                week,
                owner.id,
                now=lock_time,
                games_provider=lambda db, requested_week: _week_games(
                    db, requested_week
                ),
                line_freezer=_no_frozen_lines,
            )
            == 0
        )

        week_picks = (
            db_session.query(models.Pick)
            .filter(
                models.Pick.entry_id.in_(alive_ids),
                models.Pick.week == week,
            )
            .all()
        )
        assert len(week_picks) == len(alive_entries)
        assert all(pick.locked for pick in week_picks)
        assert all(pick.team_id is not None for pick in week_picks)
        auto_pick = next(
            pick for pick in week_picks if pick.entry_id == missing_entry_id
        )
        auto_pick_ids.append(auto_pick.id)

        # A halftime/in-progress update must not decide Survivor picks.
        in_progress = [_result(game, week, status="in_progress") for game in week_games]
        halftime_summary = apply_game_results(db_session, in_progress, now=lock_time)
        db_session.commit()
        assert halftime_summary.final_games == 0
        assert all(pick.result is None for pick in week_picks)

        final_results = [
            _result(game, week, tie=(week == 7 and index == 0))
            for index, game in enumerate(week_games)
        ]
        summary = apply_game_results(
            db_session,
            final_results,
            now=lock_time + timedelta(hours=4),
        )
        db_session.commit()
        assert summary.final_games == 16

        if week == 3:
            corrected_game = week_games[0]
            original_result = final_results[0]
            original_loser_id = (
                corrected_game.away_team_id
                if original_result.home_score > original_result.away_score
                else corrected_game.home_team_id
            )
            corrected_pick = next(
                pick for pick in week_picks if pick.team_id == original_loser_id
            )
            assert db_session.get(models.Entry, corrected_pick.entry_id).alive is False
            corrected_result = _result(corrected_game, week)
            corrected_result = NflGameResult(
                **{
                    **corrected_result.__dict__,
                    "home_score": corrected_result.away_score,
                    "away_score": corrected_result.home_score,
                }
            )
            apply_game_results(
                db_session,
                [corrected_result],
                now=lock_time + timedelta(hours=5),
            )
            db_session.commit()
            assert db_session.get(models.Entry, corrected_pick.entry_id).alive is True
            apply_game_results(
                db_session,
                [original_result],
                now=lock_time + timedelta(hours=6),
            )
            db_session.commit()
            assert db_session.get(models.Entry, corrected_pick.entry_id).alive is False
            correction_checked = True

        if week == 7:
            tie_game = week_games[0]
            tie_team_ids = {tie_game.home_team_id, tie_game.away_team_id}
            tie_picks = [pick for pick in week_picks if pick.team_id in tie_team_ids]
            assert tie_picks
            assert all(pick.result == "loss" for pick in tie_picks)
            assert all(
                db_session.get(models.Entry, pick.entry_id).alive is False
                for pick in tie_picks
            )
            tie_checked = True

        repeat = apply_game_results(
            db_session,
            final_results,
            now=lock_time + timedelta(hours=7),
        )
        db_session.commit()
        assert repeat.picks_changed == 0
        assert repeat.entries_changed == 0

        alive_after = (
            db_session.query(models.Entry)
            .filter(
                models.Entry.pool_id == pool_id,
                models.Entry.alive.is_(True),
            )
            .count()
        )
        assert 0 < alive_after <= len(alive_entries)
        alive_counts.append(alive_after)

    assert correction_checked
    assert tie_checked
    assert len(auto_pick_ids) == WEEK_COUNT
    assert len(set(auto_pick_ids)) == WEEK_COUNT
    assert all(after <= before for before, after in zip(alive_counts, alive_counts[1:]))
    assert 0 < alive_counts[-1] < alive_counts[0]

    all_picks = (
        db_session.query(models.Pick)
        .join(models.Entry)
        .filter(models.Entry.pool_id == pool_id)
        .order_by(models.Pick.entry_id, models.Pick.week)
        .all()
    )
    assert all(pick.locked for pick in all_picks)
    assert all(pick.result in {"win", "loss"} for pick in all_picks)
    picks_by_entry = defaultdict(list)
    for pick in all_picks:
        picks_by_entry[pick.entry_id].append(pick)
    for entry in entries:
        entry_picks = picks_by_entry[entry.id]
        team_ids = [pick.team_id for pick in entry_picks]
        assert len(team_ids) == len(set(team_ids)), entry.id
        losses = [pick.week for pick in entry_picks if pick.result == "loss"]
        if entry.alive:
            assert len(entry_picks) == WEEK_COUNT
            assert not losses
        else:
            assert losses
            assert max(pick.week for pick in entry_picks) == min(losses)

    pick_results = Counter(pick.result for pick in all_picks)
    assert pick_results["win"] > 0
    assert pick_results["loss"] > 0
