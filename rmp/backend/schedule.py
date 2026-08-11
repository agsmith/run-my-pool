from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from models import Schedule, Team, PoolGameLine
from deps import get_db
from odds_service import fetch_week_lines

router = APIRouter()


def current_season_games(db: Session, week_num: int):
    """Return the newest regular-season slate, excluding preseason collisions."""
    games = db.query(Schedule).filter(Schedule.week_num == week_num).all()
    if not games:
        return []

    # ESPN numbers preseason and regular-season weeks independently. Without
    # this boundary, August preseason Week 1/2 rows are mixed into September's
    # regular-season Week 1/2. NFL regular-season games are September-January.
    regular_season_games = [g for g in games if g.start_time.month >= 9 or g.start_time.month <= 2]
    if regular_season_games:
        games = regular_season_games

    season = max(g.start_time.year if g.start_time.month >= 7 else g.start_time.year - 1 for g in games)
    return sorted(
        [g for g in games if (g.start_time.year if g.start_time.month >= 7 else g.start_time.year - 1) == season],
        key=lambda game: game.start_time,
    )


def utc_isoformat(value):
    """Schedule timestamps are stored as naive UTC; label them unambiguously."""
    if value is None:
        return None
    return f"{value.isoformat()}Z"


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

    return [{
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
    games = db.query(Schedule).order_by(Schedule.week_num, Schedule.start_time).all()
    
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
