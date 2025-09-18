from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
import deps

router = APIRouter(prefix="/rules", tags=["rules"])

@router.get("/", response_model=List[schemas.RuleOut])
def get_rules(
    pool_type: str = "survivor",
    db: Session = Depends(deps.get_db)
):
    """Get all available rules for a specific pool type."""
    try:
        rules = db.query(models.Rule).filter(
            models.Rule.pool_type == pool_type
        ).all()
        return rules
    except Exception as e:
        print(f"Get rules error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve rules")

@router.get("/{rule_id}", response_model=schemas.RuleOut)
def get_rule(
    rule_id: str,
    db: Session = Depends(deps.get_db)
):
    """Get a specific rule by ID."""
    try:
        rule = db.query(models.Rule).filter(models.Rule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        return rule
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get rule error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve rule")
