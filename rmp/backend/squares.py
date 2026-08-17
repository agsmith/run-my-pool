"""Authoritative single-game 10x10 Squares boards."""

import json
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

import deps
import entitlements
import models
import schemas
from audit_utils import create_audit_log
from platform_admin import is_platform_super_admin
from pool_access import is_pool_participant

router = APIRouter(prefix="/squares", tags=["squares"])


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _pool(db: Session, pool_id: str) -> models.Pool:
    pool = (
        db.query(models.Pool)
        .options(joinedload(models.Pool.square_board))
        .filter(models.Pool.id == pool_id)
        .first()
    )
    if not pool or pool.pool_type != "squares" or not pool.square_board:
        raise HTTPException(status_code=404, detail="Squares pool not found")
    return pool


def _selected_games(pool: models.Pool) -> list[models.Schedule]:
    games = [selection.game for selection in pool.square_games]
    if not games and pool.squares_game is not None:
        games = [pool.squares_game]
    return sorted(games, key=lambda game: (game.start_time, game.game_id))


def _lock_time(pool: models.Pool) -> datetime:
    games = _selected_games(pool)
    if not games:
        raise HTTPException(status_code=409, detail="This Squares board has no selected games")
    return games[0].start_time


def _is_admin(db: Session, pool: models.Pool, user: models.User) -> bool:
    return bool(
        is_platform_super_admin(user)
        or pool.owner_id == user.id
        or db.query(models.PoolAdmin).filter(
            models.PoolAdmin.pool_id == pool.id,
            models.PoolAdmin.user_id == user.id,
        ).first()
    )


def _require_participant(db: Session, pool: models.Pool, user: models.User) -> None:
    if not is_platform_super_admin(user) and not is_pool_participant(db, pool.id, user.id):
        raise HTTPException(status_code=403, detail="Pool membership required")


def _lock_board(board: models.SquareBoard, *, actor_id: str | None = None) -> bool:
    if board.locked_at:
        return False
    generator = secrets.SystemRandom()
    board.home_digits = json.dumps(generator.sample(range(10), 10), separators=(",", ":"))
    board.away_digits = json.dumps(generator.sample(range(10), 10), separators=(",", ":"))
    board.locked_at = _now()
    board.locked_by = actor_id
    board.updated_at = board.locked_at
    return True


def ensure_board_locked_for_kickoff(db: Session, pool: models.Pool) -> bool:
    """Automatically lock at kickoff so a missing commissioner action cannot expose digits."""
    if pool.square_board.locked_at or _now() < _lock_time(pool):
        return False
    db.query(models.SquareBoard).filter(models.SquareBoard.pool_id == pool.id).with_for_update().one()
    db.refresh(pool.square_board)
    changed = _lock_board(pool.square_board)
    if changed:
        db.commit()
    return changed


def _claim_payload(claim: models.SquareClaim) -> dict:
    return {
        "id": claim.id,
        "row_index": claim.row_index,
        "column_index": claim.column_index,
        "block_number": claim.row_index * 10 + claim.column_index + 1,
        "user_id": claim.user_id,
        "user_email": claim.user.email,
        "display_name": claim.display_name,
        "claimed_at": claim.claimed_at,
    }


def _effective_total_pot(board: models.SquareBoard, claim_count: int) -> int | None:
    if board.pot_mode == "per_square":
        return board.per_square_cents * claim_count if board.per_square_cents is not None else None
    return board.total_pot_cents


def board_payload(db: Session, pool: models.Pool, user: models.User) -> dict:
    ensure_board_locked_for_kickoff(db, pool)
    db.refresh(pool.square_board)
    board = pool.square_board
    claims = db.query(models.SquareClaim).options(joinedload(models.SquareClaim.user)).filter(
        models.SquareClaim.pool_id == pool.id
    ).all()
    claims_by_cell = {(claim.row_index, claim.column_index): claim for claim in claims}
    payouts = db.query(models.SquarePayout).options(joinedload(models.SquarePayout.winner)).filter(
        models.SquarePayout.pool_id == pool.id
    ).all()
    games = _selected_games(pool)
    if not games:
        raise HTTPException(status_code=409, detail="This Squares board has no selected games")
    game_by_id = {game.game_id: game for game in games}
    primary_game = games[0]
    admin = _is_admin(db, pool, user)
    used_capacity, capacity_limit, plan = entitlements.capacity_usage(db, pool)
    commissioner_controls = plan not in ("free", "squares-plus")
    members = []
    if admin:
        members = [{"id": member.id, "email": member.email} for member in (
            db.query(models.User).join(models.PoolMember, models.PoolMember.user_id == models.User.id)
            .filter(models.PoolMember.pool_id == pool.id).order_by(models.User.email).all()
        )]
    return {
        "pool_id": pool.id,
        "pool_name": pool.name,
        "game": {
            "game_id": primary_game.game_id,
            "start_time": primary_game.start_time,
            "status": primary_game.status,
            "home_team": {"id": primary_game.home_team_id, "name": primary_game.home_team.name, "abbrv": primary_game.home_team.abbrv},
            "away_team": {"id": primary_game.away_team_id, "name": primary_game.away_team.name, "abbrv": primary_game.away_team.abbrv},
            "home_score": primary_game.home_score,
            "away_score": primary_game.away_score,
        },
        "games": [{
            "game_id": game.game_id,
            "start_time": game.start_time,
            "status": game.status,
            "home_team": {"id": game.home_team_id, "name": game.home_team.name, "abbrv": game.home_team.abbrv},
            "away_team": {"id": game.away_team_id, "name": game.away_team.name, "abbrv": game.away_team.abbrv},
            "home_score": game.home_score,
            "away_score": game.away_score,
        } for game in games],
        "lock_time": games[0].start_time,
        "locked": board.locked_at is not None,
        "locked_at": board.locked_at,
        "home_digits": json.loads(board.home_digits) if board.home_digits else None,
        "away_digits": json.loads(board.away_digits) if board.away_digits else None,
        "pot_mode": board.pot_mode or "fixed",
        "total_pot_cents": _effective_total_pot(board, len(claims)),
        "per_square_cents": board.per_square_cents,
        "payout_percentages": {"q1": board.q1_percent, "halftime": board.halftime_percent, "q3": board.q3_percent, "final": board.final_percent},
        "claims": [_claim_payload(claim) for claim in claims],
        "payouts": [{
            "game_id": payout.game_id,
            "game": {
                "home_team": game_by_id[payout.game_id].home_team.abbrv,
                "away_team": game_by_id[payout.game_id].away_team.abbrv,
            } if payout.game_id in game_by_id else None,
            "checkpoint": payout.checkpoint,
            "home_score": payout.home_score,
            "away_score": payout.away_score,
            "winning_row": payout.winning_row,
            "winning_column": payout.winning_column,
            "winner_user_id": payout.winner_user_id,
            "winner_email": payout.winner.email if payout.winner else None,
            "winner_display_name": (
                claims_by_cell[(payout.winning_row, payout.winning_column)].display_name
                if (payout.winning_row, payout.winning_column) in claims_by_cell
                else None
            ),
            "amount_cents": payout.amount_cents,
            "determined_at": payout.determined_at,
        } for payout in payouts],
        "members": members,
        "plan": plan,
        "block_limit": min(capacity_limit, 100) if capacity_limit is not None else 100,
        "permissions": {
            "is_admin": admin,
            "can_claim": board.locked_at is None and _now() < games[0].start_time and (capacity_limit is None or used_capacity < capacity_limit),
            "can_admin_assign": admin and commissioner_controls,
            "can_use_variable_pot": admin and commissioner_controls,
        },
    }


@router.get("/{pool_id}")
def get_board(pool_id: str, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    pool = _pool(db, pool_id)
    _require_participant(db, pool, current_user)
    return board_payload(db, pool, current_user)


@router.post("/{pool_id}/claims", status_code=status.HTTP_201_CREATED)
def claim_square(pool_id: str, request: schemas.SquareClaimCreate, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    pool = _pool(db, pool_id)
    _require_participant(db, pool, current_user)
    admin = _is_admin(db, pool, current_user)
    target_id = request.user_id or current_user.id
    if target_id != current_user.id and not admin:
        raise HTTPException(status_code=403, detail="Only a pool admin may assign a square to another member")
    if target_id != current_user.id and entitlements.pool_plan(db, pool) in ("free", "squares-plus"):
        raise HTTPException(status_code=403, detail="Upgrade to Commish to assign blocks for other members")
    if not is_pool_participant(db, pool.id, target_id):
        raise HTTPException(status_code=400, detail="Squares may only be assigned to pool members")
    db.query(models.SquareBoard).filter(models.SquareBoard.pool_id == pool.id).with_for_update().one()
    db.refresh(pool.square_board)
    if pool.square_board.locked_at or _now() >= _lock_time(pool):
        raise HTTPException(status_code=409, detail="This Squares board is locked")
    entitlements.enforce_entry_capacity(db, pool)
    claim = models.SquareClaim(
        id=str(uuid.uuid4()), pool_id=pool.id, row_index=request.row_index,
        column_index=request.column_index, user_id=target_id, assigned_by=current_user.id,
        display_name=request.display_name, claimed_at=_now(),
    )
    db.add(claim)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That square has already been claimed")
    block_number = claim.row_index * 10 + claim.column_index + 1
    create_audit_log(db, "CLAIM_SQUARE", f"Reserved block {block_number}", current_user.id, "square", claim.id, {"pool_id": pool.id, "assigned_to": target_id, "display_name": claim.display_name, "block_number": block_number})
    return {"id": claim.id, "row_index": claim.row_index, "column_index": claim.column_index, "block_number": block_number, "user_id": claim.user_id, "display_name": claim.display_name}


@router.delete("/{pool_id}/claims/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
def release_square(pool_id: str, claim_id: str, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    pool = _pool(db, pool_id)
    _require_participant(db, pool, current_user)
    claim = db.query(models.SquareClaim).filter(models.SquareClaim.id == claim_id, models.SquareClaim.pool_id == pool.id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Square claim not found")
    if claim.user_id != current_user.id and not _is_admin(db, pool, current_user):
        raise HTTPException(status_code=403, detail="You cannot release another member's square")
    if pool.square_board.locked_at or _now() >= _lock_time(pool):
        raise HTTPException(status_code=409, detail="This Squares board is locked")
    block_number = claim.row_index * 10 + claim.column_index + 1
    db.delete(claim)
    db.commit()
    create_audit_log(db, "RELEASE_SQUARE", f"Released block {block_number}", current_user.id, "square", claim_id, {"pool_id": pool.id, "block_number": block_number})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{pool_id}/claims/display-name")
def update_claim_display_name(
    pool_id: str,
    request: schemas.SquareDisplayNameUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Update the board-facing name on every claim owned by one member."""
    pool = _pool(db, pool_id)
    if not _is_admin(db, pool, current_user):
        raise HTTPException(status_code=403, detail="Pool admin access required")
    claims = db.query(models.SquareClaim).filter(
        models.SquareClaim.pool_id == pool.id,
        models.SquareClaim.user_id == request.user_id,
    ).all()
    if not claims:
        raise HTTPException(status_code=404, detail="No Squares reservations found for this member")
    previous_names = sorted({claim.display_name for claim in claims if claim.display_name})
    for claim in claims:
        claim.display_name = request.display_name
    db.commit()
    create_audit_log(
        db,
        "UPDATE_SQUARE_DISPLAY_NAME",
        f"Updated display name on {len(claims)} Squares reservation(s)",
        current_user.id,
        "pool_user",
        request.user_id,
        {
            "pool_id": pool.id,
            "user_id": request.user_id,
            "previous_display_names": previous_names,
            "display_name": request.display_name,
            "claim_count": len(claims),
        },
    )
    return board_payload(db, pool, current_user)


@router.post("/{pool_id}/lock")
def lock_board(pool_id: str, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    pool = _pool(db, pool_id)
    if not _is_admin(db, pool, current_user):
        raise HTTPException(status_code=403, detail="Pool admin access required")
    db.query(models.SquareBoard).filter(models.SquareBoard.pool_id == pool.id).with_for_update().one()
    db.refresh(pool.square_board)
    if pool.square_board.locked_at:
        raise HTTPException(status_code=409, detail="This Squares board is already locked")
    _lock_board(pool.square_board, actor_id=current_user.id)
    db.commit()
    create_audit_log(db, "LOCK_SQUARE_BOARD", "Randomized digits and locked Squares board", current_user.id, "pool", pool.id)
    return board_payload(db, pool, current_user)


@router.patch("/{pool_id}/payouts")
def update_payouts(pool_id: str, request: schemas.SquarePayoutConfig, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    pool = _pool(db, pool_id)
    if not _is_admin(db, pool, current_user):
        raise HTTPException(status_code=403, detail="Pool admin access required")
    if pool.square_board.locked_at or _now() >= _lock_time(pool):
        raise HTTPException(status_code=409, detail="Payout settings cannot change after the board locks")
    percentages = [request.q1_percent, request.halftime_percent, request.q3_percent, request.final_percent]
    if sum(percentages) != 100:
        raise HTTPException(status_code=400, detail="Payout percentages must total 100")
    if request.pot_mode == "per_square" and request.per_square_cents is None:
        raise HTTPException(status_code=400, detail="An amount per reserved block is required")
    if request.pot_mode == "per_square" and entitlements.pool_plan(db, pool) in ("free", "squares-plus"):
        raise HTTPException(status_code=403, detail="Upgrade to Commish to calculate the pot per reserved block")
    board = pool.square_board
    board.pot_mode = request.pot_mode
    board.total_pot_cents = request.total_pot_cents if request.pot_mode == "fixed" else None
    board.per_square_cents = request.per_square_cents if request.pot_mode == "per_square" else None
    board.q1_percent, board.halftime_percent, board.q3_percent, board.final_percent = percentages
    board.updated_at = _now()
    db.commit()
    create_audit_log(db, "UPDATE_SQUARE_PAYOUTS", "Updated Squares payout configuration", current_user.id, "pool", pool.id, request.model_dump())
    return board_payload(db, pool, current_user)
