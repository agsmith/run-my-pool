from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import models
import schemas
import deps
from typing import List

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("/", response_model=List[schemas.AuditLogOut])
def list_audit_logs(skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db)):
    return db.query(models.AuditLog).offset(skip).limit(limit).all()
