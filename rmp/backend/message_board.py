from fastapi import APIRouter, Depends, HTTPException, Query
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
from admin import verify_admin_access
from forum_safety import objectionable
from pydantic import BaseModel
from typing import Literal
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/messages", tags=["messages"])

RATE_LIMIT_COUNT = 5
RATE_LIMIT_WINDOW_MINUTES = 10


@router.get("/pool/{pool_id}", response_model=List[schemas.MessageBoardOut])
def list_pool_messages(
    pool_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    # Entry holders, pool members, and moderators can access the Forum.
    user_entries = (
        db.query(models.Entry)
        .filter(
            models.Entry.pool_id == pool_id, models.Entry.user_id == current_user.id
        )
        .first()
    )

    if not user_entries and not has_access(db, pool_id, current_user):
        raise HTTPException(
            status_code=403, detail="You must be a member of this pool to view messages"
        )

    # Get messages with user information
    messages = (
        db.query(models.MessageBoard, models.User)
        .join(models.User, models.MessageBoard.user_id == models.User.id)
        .filter(models.MessageBoard.pool_id == pool_id)
        .filter(
            ~models.MessageBoard.user_id.in_(
                db.query(models.ForumBlock.blocked_id).filter(
                    models.ForumBlock.blocker_id == current_user.id
                )
            )
        )
        .filter(
            ~models.MessageBoard.id.in_(
                db.query(models.ForumReport.message_id).filter(
                    models.ForumReport.reporter_id == current_user.id
                )
            )
        )
        .filter(
            ~models.MessageBoard.user_id.in_(
                db.query(models.ForumBan.user_id).filter(
                    models.ForumBan.pool_id == pool_id
                )
            )
        )
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

    if not user_entries and not has_access(db, pool_id, current_user):
        raise HTTPException(
            status_code=403, detail="You must be a member of this pool to post messages"
        )

    if db.get(models.ForumBan, (pool_id, current_user.id)):
        raise HTTPException(
            status_code=403,
            detail="Your posting access in this pool has been suspended. Contact support@runmypool.net to appeal.",
        )
    if objectionable(message.message):
        raise HTTPException(
            status_code=400,
            detail="Please revise your message. Harassment, threats, hate speech, and explicit content are not allowed. Contact support@runmypool.net if this was a mistake.",
        )

    # Validate message length (250 characters max)
    if len(message.message.strip()) > 250:
        raise HTTPException(
            status_code=400, detail="Message cannot exceed 250 characters"
        )

    if len(message.message.strip()) < 1:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Rate limit: max 5 messages per user per 10-minute rolling window per pool
    window_start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=RATE_LIMIT_WINDOW_MINUTES
    )
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
            "message": (
                message.message.strip()[:100] + "..."
                if len(message.message.strip()) > 100
                else message.message.strip()
            ),
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
    if message.user_id != current_user.id and not verify_admin_access(
        message.pool_id, current_user, db
    ):
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

    if not user_entries and not has_access(db, message.pool_id, current_user):
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
            "message": (
                message.message[:100] + "..."
                if len(message.message) > 100
                else message.message
            ),
            "user_email": current_user.email,
        },
    )

    db.query(models.ForumReport).filter(
        models.ForumReport.message_id == message_id, models.ForumReport.status == "open"
    ).update(
        {
            "status": "removed",
            "resolved_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "resolved_by": current_user.id,
        }
    )
    # Delete the message
    db.delete(message)
    db.commit()

    return {"message": "Message deleted successfully"}


def has_access(db, pool_id, user):
    return (
        verify_admin_access(pool_id, user, db)
        or db.get(models.PoolMember, (pool_id, user.id)) is not None
        or db.query(models.Entry.id).filter_by(pool_id=pool_id, user_id=user.id).first()
        is not None
    )


def require_access(db, pool_id, user):
    if not has_access(db, pool_id, user):
        raise HTTPException(403, "You must be a member of this pool to use the forum")


def require_moderator(db, pool_id, user):
    if not verify_admin_access(pool_id, user, db):
        raise HTTPException(403, "Pool moderator access required")


class ReportInput(BaseModel):
    reason: Literal[
        "Harassment or hate",
        "Threats or violence",
        "Sexual content",
        "Spam or scam",
        "Personal information",
        "Other",
    ]


class ReviewInput(BaseModel):
    action: Literal["dismiss", "remove", "suspend"]


@router.get("/pool/{pool_id}/safety")
def safety_state(
    pool_id: str,
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    require_access(db, pool_id, current_user)
    blocks = (
        db.query(models.User)
        .join(models.ForumBlock, models.ForumBlock.blocked_id == models.User.id)
        .filter(models.ForumBlock.blocker_id == current_user.id)
        .all()
    )
    moderator = verify_admin_access(pool_id, current_user, db)
    reports, bans = [], []
    if moderator:
        reports = [
            {
                "id": r.id,
                "message_id": r.message_id,
                "author_id": r.author_id,
                "message": r.message_snapshot,
                "reason": r.reason,
                "created_at": r.created_at.isoformat(),
            }
            for r in db.query(models.ForumReport)
            .filter_by(pool_id=pool_id, status="open")
            .order_by(models.ForumReport.created_at)
            .limit(100)
            .all()
        ]
        bans = [
            {"id": u.id, "name": public_display_name(u)}
            for u in db.query(models.User)
            .join(models.ForumBan, models.ForumBan.user_id == models.User.id)
            .filter(models.ForumBan.pool_id == pool_id)
            .all()
        ]
    return {
        "can_moderate": moderator,
        "suspended": db.get(models.ForumBan, (pool_id, current_user.id)) is not None,
        "blocks": [{"id": u.id, "name": public_display_name(u)} for u in blocks],
        "reports": reports,
        "bans": bans,
    }


@router.post("/{message_id}/report")
def report_message(
    message_id: str,
    data: ReportInput,
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    message = db.get(models.MessageBoard, message_id)
    if not message:
        raise HTTPException(404, "Message not found")
    require_access(db, message.pool_id, current_user)
    if message.user_id == current_user.id:
        raise HTTPException(400, "You can delete your own message")
    existing = (
        db.query(models.ForumReport)
        .filter_by(message_id=message_id, reporter_id=current_user.id)
        .first()
    )
    if not existing:
        recent = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        if (
            db.query(models.ForumReport)
            .filter(
                models.ForumReport.reporter_id == current_user.id,
                models.ForumReport.created_at >= recent,
            )
            .count()
            >= 20
        ):
            raise HTTPException(
                429, "Too many reports. Contact support@runmypool.net for urgent help."
            )
        db.add(
            models.ForumReport(
                id=str(uuid.uuid4()),
                pool_id=message.pool_id,
                message_id=message.id,
                reporter_id=current_user.id,
                author_id=message.user_id,
                message_snapshot=message.message,
                reason=data.reason,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return {
        "message": "Report received and message hidden from your forum. Pool and platform moderators can review it. For urgent concerns, contact support@runmypool.net."
    }


@router.put("/pool/{pool_id}/blocks/{user_id}")
def block_member(
    pool_id: str,
    user_id: str,
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    require_access(db, pool_id, current_user)
    target = db.get(models.User, user_id)
    if not target or not has_access(db, pool_id, target):
        raise HTTPException(404, "Member not found in this pool")
    if user_id == current_user.id:
        raise HTTPException(400, "You cannot block yourself")
    if not db.get(models.ForumBlock, (current_user.id, user_id)):
        db.add(
            models.ForumBlock(
                blocker_id=current_user.id,
                blocked_id=user_id,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return {"ok": True}


@router.delete("/blocks/{user_id}")
def unblock_member(
    user_id: str,
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    block = db.get(models.ForumBlock, (current_user.id, user_id))
    if block:
        db.delete(block)
        db.commit()
    return {"ok": True}


@router.post("/pool/{pool_id}/reports/{report_id}/review")
def review_report(
    pool_id: str,
    report_id: str,
    data: ReviewInput,
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    require_moderator(db, pool_id, current_user)
    report = db.get(models.ForumReport, report_id)
    if not report or report.pool_id != pool_id:
        raise HTTPException(404, "Report not found")
    if report.status != "open":
        return {"ok": True}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if data.action == "suspend":
        author = db.get(models.User, report.author_id)
        if author and verify_admin_access(pool_id, author, db):
            raise HTTPException(
                400,
                "Moderator accounts cannot be suspended here. Contact support@runmypool.net.",
            )
        if not db.get(models.ForumBan, (pool_id, report.author_id)):
            db.add(
                models.ForumBan(
                    pool_id=pool_id, user_id=report.author_id, created_at=now
                )
            )
    if data.action in ("remove", "suspend"):
        message = db.get(models.MessageBoard, report.message_id)
        if message:
            db.delete(message)
    db.query(models.ForumReport).filter_by(
        message_id=report.message_id, status="open"
    ).update(
        {"status": data.action, "resolved_at": now, "resolved_by": current_user.id}
    )
    db.commit()
    return {"ok": True}


@router.delete("/pool/{pool_id}/suspensions/{user_id}")
def restore_posting(
    pool_id: str,
    user_id: str,
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    require_moderator(db, pool_id, current_user)
    ban = db.get(models.ForumBan, (pool_id, user_id))
    if ban:
        db.delete(ban)
        db.commit()
    return {"ok": True}
