from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
import models
import schemas
import deps
from typing import List
import uuid
from datetime import datetime, timedelta, timezone
from audit_utils import log_create_operation, log_delete_operation
from public_identity import public_display_name

router = APIRouter(prefix="/messages", tags=["messages"])

RATE_LIMIT_COUNT = 5
RATE_LIMIT_WINDOW_MINUTES = 10


@router.get("/pool/{pool_id}", response_model=List[schemas.MessageBoardOut])
def list_pool_messages(
    pool_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    # Verify user has access to this pool (has entries in it)
    user_entries = (
        db.query(models.Entry)
        .filter(
            models.Entry.pool_id == pool_id, models.Entry.user_id == current_user.id
        )
        .first()
    )

    if not user_entries:
        raise HTTPException(
            status_code=403, detail="You must be a member of this pool to view messages"
        )

    # Get messages with user information
    messages = (
        db.query(models.MessageBoard, models.User)
        .join(models.User, models.MessageBoard.user_id == models.User.id)
        .filter(models.MessageBoard.pool_id == pool_id)
        .order_by(desc(models.MessageBoard.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for message, user in messages:
        message_dict = {
            "id": message.id,
            "pool_id": message.pool_id,
            "user_id": message.user_id,
            "message": message.message,
            "created_at": message.created_at.isoformat() if message.created_at else "",
            "user_display_name": public_display_name(user),
        }
        result.append(schemas.MessageBoardOut(**message_dict))

    return result


@router.post("/pool/{pool_id}", response_model=schemas.MessageBoardOut)
def post_message(
    pool_id: str,
    message: schemas.MessageBoardCreate,
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    # Verify user has access to this pool
    user_entries = (
        db.query(models.Entry)
        .filter(
            models.Entry.pool_id == pool_id, models.Entry.user_id == current_user.id
        )
        .first()
    )

    if not user_entries:
        raise HTTPException(
            status_code=403, detail="You must be a member of this pool to post messages"
        )

    # Validate message length (250 characters max)
    if len(message.message.strip()) > 250:
        raise HTTPException(
            status_code=400, detail="Message cannot exceed 250 characters"
        )

    if len(message.message.strip()) < 1:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Rate limit: max 5 messages per user per 10-minute rolling window per pool
    window_start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=RATE_LIMIT_WINDOW_MINUTES)
    recent_count = (
        db.query(models.MessageBoard)
        .filter(
            models.MessageBoard.pool_id == pool_id,
            models.MessageBoard.user_id == current_user.id,
            models.MessageBoard.created_at >= window_start,
        )
        .count()
    )
    if recent_count >= RATE_LIMIT_COUNT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: maximum {RATE_LIMIT_COUNT} messages per {RATE_LIMIT_WINDOW_MINUTES} minutes per pool.",
        )

    # Create message
    db_message = models.MessageBoard(
        id=str(uuid.uuid4()),
        pool_id=pool_id,
        user_id=current_user.id,
        message=message.message.strip(),
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    # Log message creation
    log_create_operation(
        db=db,
        entity_type="message",
        entity_id=db_message.id,
        user_id=current_user.id,
        entity_data={
            "pool_id": pool_id,
            "message": message.message.strip()[:100] + "..."
            if len(message.message.strip()) > 100
            else message.message.strip(),
            "user_email": current_user.email,
        },
    )

    # Return message with user info
    return schemas.MessageBoardOut(
        id=db_message.id,
        pool_id=db_message.pool_id,
        user_id=db_message.user_id,
        message=db_message.message,
        created_at=db_message.created_at.isoformat(),
        user_display_name=public_display_name(current_user),
    )


@router.delete("/{message_id}")
def delete_message(
    message_id: str,
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    # Find the message
    message = (
        db.query(models.MessageBoard)
        .filter(models.MessageBoard.id == message_id)
        .first()
    )

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Verify user owns this message
    if message.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You can only delete your own messages"
        )

    # Verify user still has access to the pool
    user_entries = (
        db.query(models.Entry)
        .filter(
            models.Entry.pool_id == message.pool_id,
            models.Entry.user_id == current_user.id,
        )
        .first()
    )

    if not user_entries:
        raise HTTPException(
            status_code=403, detail="You no longer have access to this pool"
        )

    # Log message deletion before deleting
    log_delete_operation(
        db=db,
        entity_type="message",
        entity_id=message.id,
        user_id=current_user.id,
        entity_data={
            "pool_id": message.pool_id,
            "message": message.message[:100] + "..."
            if len(message.message) > 100
            else message.message,
            "user_email": current_user.email,
        },
    )

    # Delete the message
    db.delete(message)
    db.commit()

    return {"message": "Message deleted successfully"}
