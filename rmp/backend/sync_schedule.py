#!/usr/bin/env python3
"""Synchronize one NFL regular-season schedule from ESPN.

The command is deliberately dry-run by default. Use ``--apply`` only after
the complete 18-week feed passes validation.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable

import httpx
from sqlalchemy.orm import Session

from database import SessionLocal
from models import PoolGameLine, Schedule, Team

ESPN_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
)
REGULAR_SEASON_WEEKS = range(1, 19)


class ScheduleSyncError(RuntimeError):
    """Raised before database changes when the source schedule is unsafe."""


@dataclass(frozen=True)
class ScheduleGame:
    game_id: int
    week_num: int
    home_abbrv: str
    away_abbrv: str
    start_time: datetime


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ScheduleSyncError(f"Game time has no timezone: {value}")
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def _parse_week(payload: dict, season: int, week: int) -> list[ScheduleGame]:
    games = []
    for event in payload.get("events", []):
        event_season = event.get("season", {})
        event_week = event.get("week", {}).get("number")
        if event_season.get("year") != season or event_season.get("type") != 2:
            raise ScheduleSyncError(
                f"ESPN returned a non-regular-season event for {season} Week {week}"
            )
        if event_week != week:
            raise ScheduleSyncError(
                f"ESPN returned Week {event_week} while requesting Week {week}"
            )

        competitions = event.get("competitions", [])
        if len(competitions) != 1:
            raise ScheduleSyncError(
                f"Game {event.get('id')} has an invalid competition"
            )
        competitors = competitions[0].get("competitors", [])
        home = [c for c in competitors if c.get("homeAway") == "home"]
        away = [c for c in competitors if c.get("homeAway") == "away"]
        if len(home) != 1 or len(away) != 1:
            raise ScheduleSyncError(
                f"Game {event.get('id')} has invalid home/away teams"
            )

        games.append(
            ScheduleGame(
                game_id=int(event["id"]),
                week_num=week,
                home_abbrv=home[0]["team"]["abbreviation"].upper(),
                away_abbrv=away[0]["team"]["abbreviation"].upper(),
                start_time=_parse_utc(event["date"]),
            )
        )
    return games


def validate_week(games: Iterable[ScheduleGame], week: int) -> list[ScheduleGame]:
    games = list(games)
    if not 13 <= len(games) <= 16:
        raise ScheduleSyncError(
            f"Week {week} has {len(games)} games; expected between 13 and 16"
        )

    game_ids = [game.game_id for game in games]
    if len(game_ids) != len(set(game_ids)):
        raise ScheduleSyncError(f"Week {week} contains duplicate game IDs")

    teams = [abbrv for game in games for abbrv in (game.home_abbrv, game.away_abbrv)]
    duplicates = sorted({team for team in teams if teams.count(team) > 1})
    if duplicates:
        raise ScheduleSyncError(
            f"Week {week} schedules teams more than once: {', '.join(duplicates)}"
        )
    return sorted(games, key=lambda game: game.start_time)


def fetch_season_schedule(
    season: int,
    request_get: Callable = httpx.get,
) -> list[ScheduleGame]:
    all_games = []
    for week in REGULAR_SEASON_WEEKS:
        response = request_get(
            ESPN_SCOREBOARD_URL,
            params={"year": season, "seasontype": 2, "week": week, "limit": 100},
            timeout=30,
        )
        response.raise_for_status()
        all_games.extend(
            validate_week(_parse_week(response.json(), season, week), week)
        )
    return all_games


def _football_season(start_time: datetime) -> int:
    return start_time.year if start_time.month >= 7 else start_time.year - 1


def sync_season_schedule(
    db: Session,
    season: int,
    games: Iterable[ScheduleGame],
    apply: bool = False,
) -> dict:
    games = list(games)
    expected_weeks = set(REGULAR_SEASON_WEEKS)
    actual_weeks = {game.week_num for game in games}
    if actual_weeks != expected_weeks:
        missing = sorted(expected_weeks - actual_weeks)
        raise ScheduleSyncError(f"Season feed is incomplete; missing weeks: {missing}")

    # Revalidate at the database boundary so callers cannot bypass safeguards.
    for week in REGULAR_SEASON_WEEKS:
        validate_week((game for game in games if game.week_num == week), week)

    teams_by_abbrv = {team.abbrv.upper(): team for team in db.query(Team).all()}
    source_abbrvs = {
        abbrv for game in games for abbrv in (game.home_abbrv, game.away_abbrv)
    }
    missing_teams = sorted(source_abbrvs - teams_by_abbrv.keys())
    if missing_teams:
        raise ScheduleSyncError(
            f"Database is missing ESPN team mappings: {', '.join(missing_teams)}"
        )

    existing = [
        game
        for game in db.query(Schedule).all()
        if _football_season(game.start_time) == season
    ]
    existing_by_id = {game.game_id: game for game in existing}
    source_ids = {game.game_id for game in games}
    stale_ids = sorted(set(existing_by_id) - source_ids)
    referenced_stale_ids = {
        game_id
        for (game_id,) in db.query(PoolGameLine.game_id)
        .filter(PoolGameLine.game_id.in_(stale_ids or [-1]))
        .all()
    }
    if referenced_stale_ids:
        raise ScheduleSyncError(
            "Cannot remove stale games with locked pool lines: "
            + ", ".join(str(game_id) for game_id in sorted(referenced_stale_ids))
        )

    created = sum(game.game_id not in existing_by_id for game in games)
    summary = {
        "season": season,
        "games": len(games),
        "created": created,
        "updated": len(games) - created,
        "removed": len(stale_ids),
        "applied": apply,
    }
    if not apply:
        return summary

    for source in games:
        target = existing_by_id.get(source.game_id)
        if target is None:
            target = Schedule(game_id=source.game_id, season=season)
            db.add(target)
        target.season = season
        target.week_num = source.week_num
        target.home_team_id = teams_by_abbrv[source.home_abbrv].id
        target.away_team_id = teams_by_abbrv[source.away_abbrv].id
        target.start_time = source.start_time

    if stale_ids:
        db.query(Schedule).filter(Schedule.game_id.in_(stale_ids)).delete(
            synchronize_session=False
        )
    db.commit()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the validated schedule. Without this flag the command is a dry run.",
    )
    args = parser.parse_args()

    games = fetch_season_schedule(args.season)
    db = SessionLocal()
    try:
        result = sync_season_schedule(db, args.season, games, apply=args.apply)
        print(result)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
