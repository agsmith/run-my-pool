from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import Schedule, Team
from deps import get_db

router = APIRouter()

@router.get("/week/{week_num}", response_model=List[dict])
def get_schedule_for_week(week_num: int, db: Session = Depends(get_db)):
    """
    Get all games for a specific week
    """
    games = db.query(Schedule).filter(Schedule.week_num == week_num).all()
    
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

@router.get("/teams/{week_num}", response_model=List[dict])
def get_teams_playing_in_week(week_num: int, db: Session = Depends(get_db)):
    """
    Get all teams playing in a specific week (for pick selection)
    """
    games = db.query(Schedule).filter(Schedule.week_num == week_num).all()
    
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
