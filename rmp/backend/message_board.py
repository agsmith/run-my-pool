from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import models
import schemas
import deps
from typing import List

router = APIRouter(prefix="/messages", tags=["messages"])

@router.get("/", response_model=List[schemas.MessageBoardOut])
def list_messages(skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db)):
    return db.query(models.MessageBoard).offset(skip).limit(limit).all()

@router.post("/", response_model=schemas.MessageBoardOut)
def post_message(message: schemas.MessageBoardOut, db: Session = Depends(deps.get_db)):
    db_message = models.MessageBoard(**message.dict())
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message
