"""
Test helper functions for the comprehensive test suite.

Provides:
- simulate_game_result: replicates Lambda game result + elimination logic
- simulate_week_results: simulate all games in a week
- advance_time: context manager to mock datetime.now() in entries.py / picks.py / message_board.py
- get_alive_entries: query alive entries for a pool
- get_entry_used_teams: query all teams picked by an entry across all weeks
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import select

from sqlalchemy.orm import Session

import models


# ---------------------------------------------------------------------------
# Game result simulation (replicates Lambda logic without AWS/boto3)
# ---------------------------------------------------------------------------


def simulate_game_result(db: Session, game_id: int, winner_team_id: int) -> None:
    """
    Simulate the Lambda's game result update for a single game.

    Sets Schedule.winning_team_id, updates Pick.result for all picks
    in that game's week matching the home/away teams, then eliminates
    entries with any loss pick.

    Args:
        db: SQLAlchemy session
        game_id: The Schedule.game_id to resolve
        winner_team_id: The Team.id of the winning team
    """
    game = db.query(models.Schedule).filter(models.Schedule.game_id == game_id).first()
    if game is None:
        raise ValueError(f"Game {game_id} not found")

    loser_team_id = (
        game.away_team_id if game.home_team_id == winner_team_id else game.home_team_id
    )

    game.winning_team_id = winner_team_id
    db.flush()

    # Update pick results for this week's matching picks
    (
        db.query(models.Pick)
        .filter(
            models.Pick.week == game.week_num,
            models.Pick.team_id == winner_team_id,
        )
        .update({"result": "win"}, synchronize_session="fetch")
    )

    (
        db.query(models.Pick)
        .filter(
            models.Pick.week == game.week_num,
            models.Pick.team_id == loser_team_id,
        )
        .update({"result": "loss"}, synchronize_session="fetch")
    )

    db.flush()
    _eliminate_losing_entries(db)
    db.commit()


def _eliminate_losing_entries(db: Session) -> None:
    """Eliminate survivor entries with losses; Pick 'Em entries always continue."""
    loss_entry_ids = select(models.Pick.entry_id).where(models.Pick.result == "loss")
    (
        db.query(models.Entry)
        .filter(
            models.Entry.id.in_(loss_entry_ids),
            models.Entry.alive == True,  # noqa: E712
            models.Entry.pool.has(models.Pool.pool_type == "survivor"),
        )
        .update({"alive": False}, synchronize_session="fetch")
    )


def simulate_week_results(
    db: Session,
    week: int,
    home_team_wins: bool = True,
) -> None:
    """
    Simulate all games in a week.

    By default, the home team wins every game.  Pass home_team_wins=False
    to make the away team win every game.

    Args:
        db: SQLAlchemy session
        week: NFL week number (1–17)
        home_team_wins: if True, home team wins; if False, away team wins
    """
    games = db.query(models.Schedule).filter(models.Schedule.week_num == week).all()
    for game in games:
        winner_id = game.home_team_id if home_team_wins else game.away_team_id
        simulate_game_result(db, game.game_id, winner_id)


# ---------------------------------------------------------------------------
# Time mocking
# ---------------------------------------------------------------------------


@contextmanager
def advance_time(target: datetime):
    """
    Context manager that patches datetime.now() in entries.py, picks.py,
    and message_board.py to return a fixed naive UTC datetime.

    Usage:
        future = datetime(2025, 9, 8, 0, 0, 0)  # after Sunday lock
        with advance_time(future):
            response = client.post("/entries/create", ...)

    Args:
        target: The datetime to return from now().  May be tz-aware or naive;
                both forms will be normalised to naive UTC (matching the
                codebase convention of .replace(tzinfo=None)).
    """
    if target.tzinfo is not None:
        naive = target.replace(tzinfo=None)
    else:
        naive = target

    # Build a mock class that returns `naive` from .now() while still
    # allowing normal datetime construction (used in the same modules).
    class _FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return target if target.tzinfo else target.replace(tzinfo=timezone.utc)
            return naive

    with (
        patch("entries.datetime", _FakeDatetime),
        patch("picks.datetime", _FakeDatetime),
        patch("message_board.datetime", _FakeDatetime),
    ):
        yield


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def get_alive_entries(db: Session, pool_id: str) -> list:
    """Return all alive Entry objects for a pool."""
    return (
        db.query(models.Entry)
        .filter(models.Entry.pool_id == pool_id, models.Entry.alive == True)  # noqa: E712
        .all()
    )


def get_entry_used_teams(db: Session, entry_id: str) -> set:
    """Return the set of team abbreviations already picked by an entry."""
    picks = db.query(models.Pick).filter(models.Pick.entry_id == entry_id).all()
    return {p.team for p in picks}


def get_entry_used_team_ids(db: Session, entry_id: str) -> set:
    """Return the set of team IDs already picked by an entry."""
    picks = db.query(models.Pick).filter(models.Pick.entry_id == entry_id).all()
    return {p.team_id for p in picks if p.team_id is not None}
