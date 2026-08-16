from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from models import Schedule, Team, PoolGameLine
from deps import get_db
from odds_service import fetch_week_lines

router = APIRouter()


def football_season(start_time: datetime) -> int:
    """Return the season year for a regular-season kickoff."""
    return start_time.year if start_time.month >= 7 else start_time.year - 1


def current_season_week(db: Session, now: Optional[datetime] = None) -> int:
    """Derive the current NFL week from the newest schedule in the database."""
    newest_start = db.query(func.max(Schedule.start_time)).scalar()
    if newest_start is None:
        return 1
    season = football_season(newest_start)
    season_start = datetime(season, 7, 1)
    season_end = datetime(season + 1, 3, 1)
    week_ends = dict(db.query(
        Schedule.week_num, func.max(Schedule.start_time)
    ).filter(
        Schedule.start_time >= season_start,
        Schedule.start_time < season_end,
    ).group_by(Schedule.week_num).all())
    current_time = now or datetime.utcnow()
    for week in sorted(week_ends):
        if current_time <= week_ends[week]:
            return week
    return max(week_ends, default=1)


def current_season_games(db: Session, week_num: int):
    """Return the newest regular-season slate, excluding preseason collisions."""
    games = db.query(Schedule).options(
        joinedload(Schedule.home_team), joinedload(Schedule.away_team)
    ).filter(Schedule.week_num == week_num).all()
    if not games:
        return []

    # ESPN numbers preseason and regular-season weeks independently. Without
    # this boundary, August preseason Week 1/2 rows are mixed into September's
    # regular-season Week 1/2. NFL regular-season games are September-January.
    regular_season_games = [g for g in games if g.start_time.month >= 9 or g.start_time.month <= 2]
    if regular_season_games:
        games = regular_season_games

    season = max(football_season(g.start_time) for g in games)
    return sorted(
        [g for g in games if football_season(g.start_time) == season],
        key=lambda game: game.start_time,
    )


def utc_isoformat(value):
    """Schedule timestamps are stored as naive UTC; label them unambiguously."""
    if value is None:
        return None
    return f"{value.isoformat()}Z"


def matchup_spread(matchup):
    """Return a sortable spread, preferring the pool's frozen official line."""
    line = matchup["official_line"] or matchup["live_line"] or {}
    spread = line.get("spread")
    return abs(float(spread)) if spread is not None else -1


@router.get("/week/{week_num}/matchups", response_model=List[dict])
def get_week_matchups(
    week_num: int, pool_id: Optional[str] = None, db: Session = Depends(get_db)
):
    """Current-season matchups with live and, when available, locked spreads."""
    games = current_season_games(db, week_num)
    live_lines = fetch_week_lines(games)
    frozen = {}
    if pool_id:
        frozen = {
            line.game_id: line
            for line in db.query(PoolGameLine).filter(
                PoolGameLine.pool_id == pool_id,
                PoolGameLine.week_num == week_num,
            )
        }

    matchups = [{
        "game_id": game.game_id,
        "week_num": game.week_num,
        "start_time": utc_isoformat(game.start_time),
        "home_team": {"id": game.home_team.id, "name": game.home_team.name, "abbrv": game.home_team.abbrv, "logo": game.home_team.logo},
        "away_team": {"id": game.away_team.id, "name": game.away_team.name, "abbrv": game.away_team.abbrv, "logo": game.away_team.logo},
        "live_line": live_lines.get(game.game_id),
        "official_line": ({
            "favorite_team_id": frozen[game.game_id].favorite_team_id,
            "spread": frozen[game.game_id].spread,
            "details": frozen[game.game_id].details,
            "provider": frozen[game.game_id].provider,
            "captured_at": frozen[game.game_id].captured_at.isoformat(),
        } if game.game_id in frozen else None),
    } for game in games]
    return sorted(matchups, key=matchup_spread, reverse=True)

@router.get("/week/{week_num}", response_model=List[dict])
def get_schedule_for_week(week_num: int, db: Session = Depends(get_db)):
    """
    Get all games for a specific week
    """
    games = current_season_games(db, week_num)
    
    result = []
    for game in games:
        result.append({
            "game_id": game.game_id,
            "week_num": game.week_num,
            "home_team": {
                "id": game.home_team.id,
                "name": game.home_team.name,
                "abbrv": game.home_team.abbrv,
                "logo": game.home_team.logo
            },
            "away_team": {
                "id": game.away_team.id,
                "name": game.away_team.name,
                "abbrv": game.away_team.abbrv,
                "logo": game.away_team.logo
            },
            "start_time": utc_isoformat(game.start_time),
            "winning_team_id": game.winning_team_id
        })
    
    return result

@router.get("/teams/{week_num}", response_model=List[dict])
def get_teams_playing_in_week(week_num: int, db: Session = Depends(get_db)):
    """
    Get all teams playing in a specific week (for pick selection)
    """
    games = current_season_games(db, week_num)
    
    teams_set = set()
    for game in games:
        teams_set.add((game.home_team.id, game.home_team.name, game.home_team.abbrv, game.home_team.logo))
        teams_set.add((game.away_team.id, game.away_team.name, game.away_team.abbrv, game.away_team.logo))
    
    # Convert to list and sort by team abbreviation
    teams_list = [
        {
            "id": team_id,
            "name": name,
            "abbrv": abbrv,
            "logo": logo
        }
        for team_id, name, abbrv, logo in sorted(teams_set, key=lambda x: x[2])
    ]
    
    return teams_list

@router.get("/", response_model=List[dict])
def get_all_schedules(db: Session = Depends(get_db)):
    """
    Get all scheduled games
    """
    games = db.query(Schedule).options(
        joinedload(Schedule.home_team), joinedload(Schedule.away_team)
    ).order_by(Schedule.week_num, Schedule.start_time).all()
    
    result = []
    for game in games:
        result.append({
            "game_id": game.game_id,
            "week_num": game.week_num,
            "home_team": {
                "id": game.home_team.id,
                "name": game.home_team.name,
                "abbrv": game.home_team.abbrv,
                "logo": game.home_team.logo
            },
            "away_team": {
                "id": game.away_team.id,
                "name": game.away_team.name,
                "abbrv": game.away_team.abbrv,
                "logo": game.away_team.logo
            },
            "start_time": game.start_time.isoformat() if game.start_time else None,
            "winning_team_id": game.winning_team_id
        })
    
    return result
