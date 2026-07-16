from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
import deps
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/leagues", tags=["leagues"])

@router.post("/create", response_model=schemas.LeagueOut)
def create_league(
    league: schemas.LeagueCreate, 
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Create a new league with the current user as the owner/admin."""
    try:
        # Parse lock_time if provided
        lock_time = None
        if league.lock_time:
            try:
                # Handle various datetime formats
                time_str = league.lock_time.strip()
                
                # If it's ISO format with 'T', convert to MySQL format
                if 'T' in time_str:
                    # Remove 'Z' timezone indicator if present
                    time_str = time_str.replace('Z', '')
                    # Split at 'T' to separate date and time
                    date_part, time_part = time_str.split('T')
                    # Remove milliseconds if present
                    if '.' in time_part:
                        time_part = time_part.split('.')[0]
                    # Combine date and time with space
                    time_str = f"{date_part} {time_part}"
                
                # Add seconds if not present (HTML5 datetime-local doesn't include seconds)
                if len(time_str.split(' ')[1].split(':')) == 2:
                    time_str += ':00'
                
                # Parse the datetime string
                lock_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                
            except (ValueError, TypeError) as e:
                raise HTTPException(status_code=400, detail=f"Invalid lock_time format. Use YYYY-MM-DD HH:MM:SS or ISO format: {str(e)}")
        
        db_league = models.League(
            id=str(uuid.uuid4()),
            name=league.name,
            description=league.description,
            lock_time=lock_time,
            is_private=league.is_private,
            owner_id=current_user.id,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        
        db.add(db_league)
        db.commit()
        db.refresh(db_league)
        
        # Handle rule values if provided
        if league.rule_values:
            for rule_value in league.rule_values:
                db_rule_value = models.PoolRuleValue(
                    pool_id=db_league.id,
                    rule_id=rule_value.rule_id,
                    rule_value=rule_value.rule_value
                )
                db.add(db_rule_value)
            db.commit()
        
        return db_league
    except Exception as e:
        print(f"Create league error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create league")

@router.get("/my-leagues", response_model=List[schemas.LeagueOut])
def get_my_leagues(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get all leagues where the current user is the owner or a member."""
    try:
        # Get leagues where user is the owner
        owned_leagues = db.query(models.League).filter(
            models.League.owner_id == current_user.id
        ).all()
        
        # TODO: Add leagues where user is a member (requires league membership table)
        # For now, just return owned leagues
        
        return owned_leagues
    except Exception as e:
        print(f"Get my leagues error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve leagues")

@router.get("/", response_model=List[schemas.LeagueOut])
def list_leagues(skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db)):
    return db.query(models.League).offset(skip).limit(limit).all()

@router.get("/{league_id}", response_model=schemas.LeagueOut)
def get_league(
    league_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get a specific league by ID."""
    try:
        league = db.query(models.League).filter(models.League.id == league_id).first()
        
        if not league:
            raise HTTPException(status_code=404, detail="League not found")
        
        # TODO: Check if user has access to this league (owner or member)
        # For now, allow access to any league
        
        return league
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get league error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve league")

@router.patch("/{league_id}", response_model=schemas.LeagueOut)
def update_league(
    league_id: str, 
    league_update: schemas.LeagueUpdate, 
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Update a league (only by the league owner)."""
    try:
        league = db.query(models.League).filter(models.League.id == league_id).first()
        
        if not league:
            raise HTTPException(status_code=404, detail="League not found")
        
        if league.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only league owner can update the league")
        
        # Update fields if provided
        if league_update.name is not None:
            league.name = league_update.name
        if league_update.description is not None:
            league.description = league_update.description
        if league_update.lock_time is not None:
            league.lock_time = league_update.lock_time
        if league_update.is_private is not None:
            league.is_private = league_update.is_private
        
        # Handle rule values if provided
        if league_update.rule_values is not None:
            # Remove existing rule values
            db.query(models.PoolRuleValue).filter(
                models.PoolRuleValue.pool_id == league_id
            ).delete()
            
            # Add new rule values
            for rule_value in league_update.rule_values:
                db_rule_value = models.PoolRuleValue(
                    pool_id=league_id,
                    rule_id=rule_value.rule_id,
                    rule_value=rule_value.rule_value
                )
                db.add(db_rule_value)
        
        league.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        db.commit()
        db.refresh(league)
        
        return league
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update league error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update league")

@router.delete("/{league_id}")
def delete_league(
    league_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Delete a league (only by the league owner)."""
    try:
        league = db.query(models.League).filter(models.League.id == league_id).first()
        
        if not league:
            raise HTTPException(status_code=404, detail="League not found")
        
        if league.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only league owner can delete the league")
        
        # TODO: Check if league has entries before deletion
        # For now, allow deletion
        
        db.delete(league)
        db.commit()
        
        return {"message": "League deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete league error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete league")
