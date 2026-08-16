from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import Team
from deps import get_db

router = APIRouter()

@router.get("/", response_model=List[dict])
def get_teams(db: Session = Depends(get_db)):
    """
    Get all teams
    """
    teams = db.query(Team).order_by(Team.id).all()
    return [
        {
            "id": team.id,
            "name": team.name,
            "abbrv": team.abbrv,
            "logo": team.logo
        }
        for team in teams
    ]

@router.get("/{team_id}", response_model=dict)
def get_team(team_id: int, db: Session = Depends(get_db)):
    """
    Get a specific team by ID
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return {
        "id": team.id,
        "name": team.name,
        "abbrv": team.abbrv,
        "logo": team.logo
    }

@router.get("/by-abbreviation/{abbreviation}", response_model=dict)
def get_team_by_abbreviation(abbreviation: str, db: Session = Depends(get_db)):
    """
    Get a team by abbreviation
    """
    team = db.query(Team).filter(Team.abbrv == abbreviation).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return {
        "id": team.id,
        "name": team.name,
        "abbrv": team.abbrv,
        "logo": team.logo
    }
