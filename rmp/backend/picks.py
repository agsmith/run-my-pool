from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
import uuid
from datetime import datetime, timezone

from deps import get_db, get_current_user
from models import Pick, Entry
from schemas import PickCreate, PickUpdate, PickOut

router = APIRouter()

@router.post("/picks/create", response_model=PickOut)
async def create_pick(
    pick: PickCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Verify the entry belongs to the current user
    entry = db.query(Entry).filter(Entry.id == pick.entry_id, Entry.user_id == current_user.id).first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found or doesn't belong to you"
        )
    
    # Check if a pick already exists for this entry and week
    existing_pick = db.query(Pick).filter(
        and_(Pick.entry_id == pick.entry_id, Pick.week == pick.week)
    ).first()
    
    if existing_pick:
        # Update existing pick
        existing_pick.team = pick.team
        existing_pick.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing_pick)
        return existing_pick
    
    # Check if the team has already been used in this entry
    team_already_used = db.query(Pick).filter(
        and_(Pick.entry_id == pick.entry_id, Pick.team == pick.team)
    ).first()
    
    if team_already_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team {pick.team} has already been selected in this entry"
        )
    
    # Create new pick
    db_pick = Pick(
        id=str(uuid.uuid4()),
        entry_id=pick.entry_id,
        week=pick.week,
        team=pick.team,
        locked=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db.add(db_pick)
    db.commit()
    db.refresh(db_pick)
    return db_pick

@router.get("/picks/entry/{entry_id}", response_model=List[PickOut])
async def get_picks_for_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Verify the entry belongs to the current user
    entry = db.query(Entry).filter(Entry.id == entry_id, Entry.user_id == current_user.id).first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found or doesn't belong to you"
        )
    
    picks = db.query(Pick).filter(Pick.entry_id == entry_id).order_by(Pick.week).all()
    return picks

@router.put("/picks/{pick_id}", response_model=PickOut)
async def update_pick(
    pick_id: str,
    pick_update: PickUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Get the pick and verify ownership through entry
    pick = db.query(Pick).join(Entry).filter(
        Pick.id == pick_id,
        Entry.user_id == current_user.id
    ).first()
    
    if not pick:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pick not found or doesn't belong to you"
        )
    
    # Check if pick is locked
    if pick.locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a locked pick"
        )
    
    # If updating team, check if the new team is already used in this entry
    if pick_update.team and pick_update.team != pick.team:
        team_already_used = db.query(Pick).filter(
            and_(
                Pick.entry_id == pick.entry_id, 
                Pick.team == pick_update.team,
                Pick.id != pick_id
            )
        ).first()
        
        if team_already_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team {pick_update.team} has already been selected in this entry"
            )
    
    # Update fields
    for field, value in pick_update.dict(exclude_unset=True).items():
        setattr(pick, field, value)
    
    pick.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pick)
    return pick

@router.delete("/picks/{pick_id}")
async def delete_pick(
    pick_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Get the pick and verify ownership through entry
    pick = db.query(Pick).join(Entry).filter(
        Pick.id == pick_id,
        Entry.user_id == current_user.id
    ).first()
    
    if not pick:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pick not found or doesn't belong to you"
        )
    
    # Check if pick is locked
    if pick.locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a locked pick"
        )
    
    db.delete(pick)
    db.commit()
    return {"message": "Pick deleted successfully"}
