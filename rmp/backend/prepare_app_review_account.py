#!/usr/bin/env python3
"""Prepare the fixed App Review member account and deterministic demo content.

The command is idempotent. It updates the password only for the review account,
never stores the plaintext password, and creates private participant-only demo
pools backed by the current schedule already present in the target database.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import uuid
from datetime import datetime, time, timedelta

from passlib.context import CryptContext
from sqlalchemy import func
from sqlalchemy.orm import joinedload

import models
from database import SessionLocal


REVIEW_EMAIL = "zz_test_member@gmail.com"
NAMESPACE = uuid.UUID("a8254673-7caf-4918-96d5-f6a7b71da15c")
PASSWORDS = CryptContext(schemes=["bcrypt"], deprecated="auto")


def stable_id(key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, key))


def naive_utc_now() -> datetime:
    return datetime.utcnow()


def football_season(start_time: datetime) -> int:
    return start_time.year if start_time.month >= 7 else start_time.year - 1


def current_season_games(db, week: int):
    rows = (
        db.query(models.Schedule)
        .options(
            joinedload(models.Schedule.home_team),
            joinedload(models.Schedule.away_team),
        )
        .filter(models.Schedule.week_num == week)
        .all()
    )
    regular = [game for game in rows if game.start_time.month >= 9 or game.start_time.month <= 2]
    rows = regular or rows
    if not rows:
        return []
    season = max(football_season(game.start_time) for game in rows)
    return sorted(
        [game for game in rows if football_season(game.start_time) == season],
        key=lambda game: game.start_time,
    )


def current_season_week(db, now: datetime) -> int:
    newest_start = db.query(func.max(models.Schedule.start_time)).scalar()
    if newest_start is None:
        return 1
    season = football_season(newest_start)
    week_ends = dict(
        db.query(models.Schedule.week_num, func.max(models.Schedule.start_time))
        .filter(
            models.Schedule.start_time >= datetime(season, 7, 1),
            models.Schedule.start_time < datetime(season + 1, 3, 1),
        )
        .group_by(models.Schedule.week_num)
        .all()
    )
    for week in sorted(week_ends):
        if now <= week_ends[week]:
            return week
    return max(week_ends, default=1)


def upsert_by_id(db, model, key: str, **values):
    identifier = stable_id(key)
    row = db.get(model, identifier)
    if row is None:
        row = model(id=identifier)
        db.add(row)
    for name, value in values.items():
        setattr(row, name, value)
    return row


def ensure_user(db, email: str, display_name: str, password: str | None = None):
    row = db.query(models.User).filter(func.lower(models.User.email) == email.lower()).first()
    now = naive_utc_now()
    if row is None:
        row = models.User(
            id=stable_id(f"user:{email.lower()}"),
            email=email.lower(),
            hashed_password=PASSWORDS.hash(password or secrets.token_urlsafe(32)),
            created_at=now,
        )
        db.add(row)
    elif password:
        row.hashed_password = PASSWORDS.hash(password)
    row.display_name = display_name
    row.is_active = True
    row.email_verified = True
    row.role = models.UserRole.USER
    row.updated_at = now
    return row


def ensure_pool(db, key: str, *, owner, name: str, pool_type: str, game=None):
    now = naive_utc_now()
    row = upsert_by_id(
        db,
        models.Pool,
        f"pool:{key}",
        name=name,
        description="Private pre-populated pool used by Apple App Review.",
        pool_type=pool_type,
        survivor_objective="win",
        survivor_mulligans=0,
        pickem_games_per_week=4 if pool_type == "pickem" else None,
        pickem_slate="all",
        squares_game_id=game.game_id if game is not None else None,
        lock_time=now - timedelta(days=1),
        lock_day_of_week=6,
        lock_time_of_day=time(13, 0),
        lock_timezone="America/New_York",
        join_lock_time=now - timedelta(days=1),
        is_private=True,
        owner_id=owner.id,
        billing_entitlement_id=None,
        billing_season=football_season(game.start_time) if game is not None else now.year,
        created_at=now - timedelta(days=30),
        updated_at=now,
    )
    return row


def ensure_membership(db, pool, user, joined_at):
    row = db.query(models.PoolMember).filter_by(pool_id=pool.id, user_id=user.id).first()
    if row is None:
        row = models.PoolMember(pool_id=pool.id, user_id=user.id)
        db.add(row)
    row.joined_at = joined_at
    row.dues_paid = False
    row.weekly_recap_enabled = False
    row.notes = None
    return row


def ensure_entry(db, key: str, pool, user, name: str, *, alive=True):
    now = naive_utc_now()
    return upsert_by_id(
        db,
        models.Entry,
        f"entry:{key}",
        user_id=user.id,
        pool_id=pool.id,
        name=name,
        manual_participant_name=None,
        alive=alive,
        created_at=now - timedelta(days=21),
        updated_at=now,
    )


def ensure_pick(
    db,
    key: str,
    entry,
    week: int,
    team,
    *,
    game=None,
    result: str | None = None,
    locked=True,
):
    now = naive_utc_now()
    return upsert_by_id(
        db,
        models.Pick,
        f"pick:{key}",
        entry_id=entry.id,
        week=week,
        game_id=game.game_id if game is not None else None,
        team=team.abbrv,
        team_id=team.id,
        locked=locked,
        result=result,
        created_at=now - timedelta(days=7),
        updated_at=now,
    )


def selected_team(game, wants_winner: bool):
    if game.winning_team_id in {game.home_team_id, game.away_team_id}:
        winner = game.home_team if game.winning_team_id == game.home_team_id else game.away_team
        loser = game.away_team if winner.id == game.home_team_id else game.home_team
        return winner if wants_winner else loser
    return game.home_team if wants_winner else game.away_team


def seed_review_content(db, password: str) -> dict:
    now = naive_utc_now()
    reviewer = ensure_user(db, REVIEW_EMAIL, "App Review Member", password)
    writers = [
        ensure_user(db, "appreview.writer@runmypool.net", "Casey Writer"),
        ensure_user(db, "appreview.analyst@runmypool.net", "Jordan Analyst"),
        ensure_user(db, "appreview.player@runmypool.net", "Morgan Player"),
    ]
    db.flush()

    # The review login must remain an ordinary participant even if the command
    # is re-run after someone temporarily granted it an administrator role.
    db.query(models.PoolAdmin).filter(models.PoolAdmin.user_id == reviewer.id).delete(
        synchronize_session=False
    )

    current_week = current_season_week(db, now)
    current_games = current_season_games(db, current_week)
    if not current_games:
        raise RuntimeError("The current NFL schedule is empty; sync the schedule before preparing App Review data.")
    available_weeks = sorted(
        week for (week,) in db.query(models.Schedule.week_num).distinct().all()
        if current_season_games(db, week)
    )
    past_weeks = [week for week in available_weeks if week < current_week]
    history_week = past_weeks[-1] if past_weeks else current_week
    history_games = current_season_games(db, history_week)
    if len(history_games) < 4:
        raise RuntimeError("At least four scheduled games are required to create review standings.")

    owner = writers[0]
    survivor = ensure_pool(
        db, "survivor", owner=owner, name="App Review Survivor Demo", pool_type="survivor"
    )
    pickem = ensure_pool(
        db, "pickem", owner=owner, name="App Review Pick 'Em Demo", pool_type="pickem"
    )
    squares = ensure_pool(
        db,
        "squares",
        owner=owner,
        name="App Review Squares Demo",
        pool_type="squares",
        game=history_games[0],
    )
    people = [reviewer, *writers]
    for pool in (survivor, pickem, squares):
        for person in people:
            ensure_membership(db, pool, person, now - timedelta(days=24))
    db.flush()

    survivor_entries = [
        ensure_entry(db, "survivor-reviewer", survivor, reviewer, "Review Entry"),
        ensure_entry(db, "survivor-writer", survivor, writers[0], "Sunday Special", alive=False),
        ensure_entry(db, "survivor-analyst", survivor, writers[1], "Upset Alert"),
        ensure_entry(db, "survivor-player", survivor, writers[2], "Still Standing"),
    ]
    survivor_choices = [
        (history_games[0], True, "win"),
        (history_games[1], False, "loss"),
        (history_games[2], True, "win"),
        (history_games[3], True, "win"),
    ]
    for index, (entry, choice) in enumerate(zip(survivor_entries, survivor_choices)):
        game, wants_winner, result = choice
        ensure_pick(
            db,
            f"survivor-history-{index}",
            entry,
            history_week,
            selected_team(game, wants_winner),
            result=result,
            locked=True,
        )

    db.flush()
    auto_entry = survivor_entries[2]
    auto_pick = db.get(models.Pick, stable_id("pick:survivor-history-2"))
    audit_details = {
        "description": "App Review demo auto-pick",
        "timestamp": now.isoformat(),
        "entity_type": "pick",
        "entity_id": auto_pick.id,
        "additional_data": {
            "pool_id": survivor.id,
            "entry_id": auto_entry.id,
            "week": history_week,
            "team": auto_pick.team,
            "reason": "no_pick_at_lock",
        },
    }
    upsert_by_id(
        db,
        models.AuditLog,
        "audit:survivor-auto-pick",
        user_id=owner.id,
        action="ADMIN_AUTO_PICK",
        details=json.dumps(audit_details),
        created_at=now - timedelta(days=6),
        ip_address=None,
        country=None,
        city=None,
    )

    pickem_entries = [
        ensure_entry(db, "pickem-reviewer", pickem, reviewer, "Review Picks"),
        ensure_entry(db, "pickem-writer", pickem, writers[0], "Press Box"),
        ensure_entry(db, "pickem-analyst", pickem, writers[1], "Numbers Game"),
        ensure_entry(db, "pickem-player", pickem, writers[2], "Monday Rally"),
    ]
    for entry_index, entry in enumerate(pickem_entries):
        for game_index, game in enumerate(history_games[:4]):
            winner = (entry_index + game_index) % 3 != 0
            ensure_pick(
                db,
                f"pickem-history-{entry_index}-{game_index}",
                entry,
                history_week,
                selected_team(game, winner),
                game=game,
                result="win" if winner else "loss",
                locked=True,
            )
        upsert_by_id(
            db,
            models.PickEmTiebreaker,
            f"tiebreaker:{entry.id}:{history_week}",
            entry_id=entry.id,
            week=history_week,
            predicted_total=40 + entry_index * 3,
            created_at=now - timedelta(days=7),
            updated_at=now,
        )

    board = db.get(models.SquareBoard, squares.id)
    if board is None:
        board = models.SquareBoard(pool_id=squares.id)
        db.add(board)
    board.home_digits = "0,1,2,3,4,5,6,7,8,9"
    board.away_digits = "9,8,7,6,5,4,3,2,1,0"
    board.pot_mode = "fixed"
    board.total_pot_cents = None
    board.per_square_cents = None
    board.q1_percent = board.halftime_percent = board.q3_percent = board.final_percent = 25
    board.locked_at = now - timedelta(days=2)
    board.locked_by = owner.id
    board.created_at = now - timedelta(days=21)
    board.updated_at = now
    square_game = db.query(models.PoolSquareGame).filter_by(
        pool_id=squares.id, game_id=history_games[0].game_id
    ).first()
    if square_game is None:
        square_game = models.PoolSquareGame(
            pool_id=squares.id, game_id=history_games[0].game_id
        )
        db.add(square_game)
    square_game.display_order = 0
    square_game.created_at = now - timedelta(days=21)
    for index, person in enumerate(people):
        upsert_by_id(
            db,
            models.SquareClaim,
            f"square-claim:{person.id}",
            pool_id=squares.id,
            row_index=index,
            column_index=(index * 2) % 10,
            user_id=person.id,
            assigned_by=owner.id,
            display_name=person.display_name,
            claimed_at=now - timedelta(days=14),
        )
    game = history_games[0]
    home_score = game.home_score if game.home_score is not None else 17
    away_score = game.away_score if game.away_score is not None else 13
    upsert_by_id(
        db,
        models.SquarePayout,
        "square-payout:final",
        pool_id=squares.id,
        game_id=game.game_id,
        checkpoint="final",
        home_score=home_score,
        away_score=away_score,
        winning_row=home_score % 10,
        winning_column=away_score % 10,
        winner_user_id=reviewer.id,
        amount_cents=None,
        determined_at=now - timedelta(days=1),
    )

    forum_copy = [
        "Welcome to the review pool. The weekly slate is ready.",
        "I like the underdog in the late game. Good luck this week!",
        "The standings are tight heading into the final matchup.",
    ]
    for pool in (survivor, pickem, squares):
        for index, copy in enumerate(forum_copy):
            upsert_by_id(
                db,
                models.MessageBoard,
                f"message:{pool.id}:{index}",
                pool_id=pool.id,
                user_id=writers[index].id,
                message=copy,
                created_at=now - timedelta(hours=8 - index),
            )

    db.commit()
    return review_summary(db, reviewer.id)


def review_summary(db, reviewer_id: str) -> dict:
    reviewer = db.get(models.User, reviewer_id)
    pools = (
        db.query(models.Pool)
        .join(models.PoolMember, models.PoolMember.pool_id == models.Pool.id)
        .filter(
            models.PoolMember.user_id == reviewer_id,
            models.Pool.name.like("App Review % Demo"),
        )
        .order_by(models.Pool.pool_type)
        .all()
    )
    return {
        "email": reviewer.email if reviewer else REVIEW_EMAIL,
        "active": bool(reviewer and reviewer.is_active),
        "email_verified": bool(reviewer and reviewer.email_verified),
        "role": reviewer.role.value if reviewer else None,
        "pool_admin_grants": db.query(models.PoolAdmin).filter_by(user_id=reviewer_id).count(),
        "pools": [
            {
                "id": pool.id,
                "name": pool.name,
                "type": pool.pool_type,
                "entries": db.query(models.Entry).filter_by(pool_id=pool.id).count(),
                "messages": db.query(models.MessageBoard).filter_by(pool_id=pool.id).count(),
                "square_claims": db.query(models.SquareClaim).filter_by(pool_id=pool.id).count(),
            }
            for pool in pools
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--password-env",
        default="APP_REVIEW_PASSWORD",
        help="Environment variable containing the review account password.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Print the current review-account state without changing it.",
    )
    args = parser.parse_args()
    db = SessionLocal()
    try:
        reviewer = db.query(models.User).filter(
            func.lower(models.User.email) == REVIEW_EMAIL
        ).first()
        if args.verify_only:
            if reviewer is None:
                raise RuntimeError(f"Review account {REVIEW_EMAIL} does not exist.")
            print(json.dumps(review_summary(db, reviewer.id), indent=2))
            return 0
        password = os.getenv(args.password_env)
        if not password:
            raise RuntimeError(
                f"Set {args.password_env} to the review password before running this command."
            )
        print(json.dumps(seed_review_content(db, password), indent=2))
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
