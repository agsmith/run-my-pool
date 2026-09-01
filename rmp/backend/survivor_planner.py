"""Private Survivor season planning endpoints.

Plans are deliberately excluded from commissioner and platform-admin APIs and
from audit details. They are not picks until their owner explicitly promotes a
current-week plan through the normal pick creation path.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from admin import is_user_locked_in_pool
from deps import get_current_user, get_db
from models import Entry, Pick, Pool, PoolGameLine, SurvivorEntryPlan, Team
from picks import _check_pick_lock, _validate_survivor_team, create_pick
from pool_access import is_pool_participant
from schedule import current_season_games, current_season_week, utc_isoformat
from schemas import PickCreate, SurvivorPlanUpdate

router = APIRouter(prefix="/survivor-planner", tags=["survivor-planner"])


def _pool(db: Session, pool_id: str) -> Pool:
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    if pool.pool_type != "survivor":
        raise HTTPException(status_code=400, detail="Season planning is only available for Survivor pools")
    return pool


def _owned_entry(db: Session, entry_id: str, user_id: str) -> Entry:
    entry = db.query(Entry).filter(Entry.id == entry_id, Entry.user_id == user_id).first()
    if not entry:
        # Do not disclose whether another user's private entry exists.
        raise HTTPException(status_code=404, detail="Entry not found")
    _pool(db, entry.pool_id)
    return entry


def _assert_mutable(db: Session, entry: Entry, week_num: int, team: Team | None = None):
    if not 1 <= week_num <= 18:
        raise HTTPException(status_code=422, detail="Week must be between 1 and 18")
    if not entry.alive:
        raise HTTPException(status_code=403, detail="Entry has been eliminated")
    if is_user_locked_in_pool(db, entry.pool_id, entry.user_id):
        raise HTTPException(status_code=423, detail="Your account is locked in this pool. Contact the pool admin.")
    current_week = current_season_week(db)
    if week_num < current_week:
        raise HTTPException(status_code=423, detail="Past weeks cannot be planned")
    pool = db.query(Pool).filter(Pool.id == entry.pool_id).first()
    if team is not None:
        _validate_survivor_team(db, pool, team, week_num)
        if week_num == current_week:
            _check_pick_lock(db, pool, team.abbrv, week_num)


def _team_json(team: Team):
    return {"id": team.id, "name": team.name, "abbrv": team.abbrv, "logo": team.logo}


def _line_json(line):
    if not line:
        return None
    return {
        "favorite_team_id": line.favorite_team_id,
        "spread": line.spread,
        "details": line.details,
        "provider": line.provider,
        "captured_at": utc_isoformat(line.captured_at),
    }


@router.get("/pools/{pool_id}")
def get_planner(pool_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    pool = _pool(db, pool_id)
    if not is_pool_participant(db, pool_id, current_user.id):
        raise HTTPException(status_code=403, detail="Pool membership required")

    entries = db.query(Entry).filter(Entry.pool_id == pool_id, Entry.user_id == current_user.id).order_by(Entry.name).all()
    entry_ids = [entry.id for entry in entries]
    picks = db.query(Pick).options(joinedload(Pick.team_obj)).filter(Pick.entry_id.in_(entry_ids)).all() if entry_ids else []
    plans = db.query(SurvivorEntryPlan).options(joinedload(SurvivorEntryPlan.team)).filter(SurvivorEntryPlan.entry_id.in_(entry_ids)).all() if entry_ids else []
    picks_by_entry = {entry_id: [] for entry_id in entry_ids}
    plans_by_entry = {entry_id: [] for entry_id in entry_ids}
    for pick in picks:
        picks_by_entry[pick.entry_id].append({"id": pick.id, "week": pick.week, "team": pick.team, "team_id": pick.team_id, "locked": pick.locked, "result": pick.result})
    for plan in plans:
        plans_by_entry[plan.entry_id].append({"id": plan.id, "week": plan.week_num, "team": plan.team.abbrv, "team_id": plan.team_id})

    games = [game for week in range(1, 19) for game in current_season_games(db, week)]
    frozen = {(line.game_id, line.week_num): line for line in db.query(PoolGameLine).filter(PoolGameLine.pool_id == pool_id).all()}
    weeks = {week: [] for week in range(1, 19)}
    for game in games:
        line = frozen.get((game.game_id, game.week_num))
        weeks[game.week_num].append({
            "game_id": game.game_id, "start_time": utc_isoformat(game.start_time),
            "home_team": _team_json(game.home_team), "away_team": _team_json(game.away_team),
            "winning_team_id": game.winning_team_id,
            "official_line": _line_json(line),
        })
    return {
        "pool": {"id": pool.id, "name": pool.name, "pool_type": pool.pool_type, "survivor_objective": pool.survivor_objective},
        "current_week": current_season_week(db),
        "entries": [{"id": entry.id, "name": entry.name, "alive": entry.alive, "picks": picks_by_entry[entry.id], "plans": plans_by_entry[entry.id]} for entry in entries],
        "weeks": [{"week": week, "games": weeks[week]} for week in range(1, 19)],
    }
@router.put("/entries/{entry_id}/weeks/{week_num}")
def save_plan(entry_id: str, week_num: int, payload: SurvivorPlanUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    entry = _owned_entry(db, entry_id, current_user.id)
    team = db.query(Team).filter(Team.abbrv == payload.team).first()
    _assert_mutable(db, entry, week_num, team)
    if not team:
        raise HTTPException(status_code=400, detail="Selected team is not recognized")
    official = db.query(Pick).filter(Pick.entry_id == entry.id, Pick.week == week_num, Pick.game_id.is_(None)).first()
    if official:
        raise HTTPException(status_code=409, detail="This week already has an official pick")
    if db.query(Pick).filter(Pick.entry_id == entry.id, Pick.team_id == team.id).first():
        raise HTTPException(status_code=409, detail=f"Team {team.abbrv} has already been used")
    duplicate_plan = db.query(SurvivorEntryPlan).filter(SurvivorEntryPlan.entry_id == entry.id, SurvivorEntryPlan.team_id == team.id, SurvivorEntryPlan.week_num != week_num).first()
    if duplicate_plan:
        raise HTTPException(status_code=409, detail=f"Team {team.abbrv} is already planned for week {duplicate_plan.week_num}")
    plan = db.query(SurvivorEntryPlan).filter(SurvivorEntryPlan.entry_id == entry.id, SurvivorEntryPlan.week_num == week_num).first()
    now = datetime.now(timezone.utc)
    if plan:
        plan.team_id = team.id
        plan.updated_at = now
    else:
        plan = SurvivorEntryPlan(id=str(uuid.uuid4()), entry_id=entry.id, week_num=week_num, team_id=team.id, created_at=now, updated_at=now)
        db.add(plan)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That team or week was planned in another request")
    return {"id": plan.id, "entry_id": entry.id, "week": week_num, "team": team.abbrv, "team_id": team.id}


@router.delete("/entries/{entry_id}/weeks/{week_num}")
def delete_plan(entry_id: str, week_num: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    entry = _owned_entry(db, entry_id, current_user.id)
    _assert_mutable(db, entry, week_num)
    plan = db.query(SurvivorEntryPlan).filter(SurvivorEntryPlan.entry_id == entry.id, SurvivorEntryPlan.week_num == week_num).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    db.delete(plan)
    db.commit()
    return {"message": "Plan removed"}


@router.post("/entries/{entry_id}/weeks/{week_num}/make-official")
async def make_official(entry_id: str, week_num: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    entry = _owned_entry(db, entry_id, current_user.id)
    if week_num != current_season_week(db):
        raise HTTPException(status_code=400, detail="Only the current week's plan can become an official pick")
    plan = db.query(SurvivorEntryPlan).options(joinedload(SurvivorEntryPlan.team)).filter(SurvivorEntryPlan.entry_id == entry.id, SurvivorEntryPlan.week_num == week_num).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    result = await create_pick(PickCreate(entry_id=entry.id, week=week_num, team=plan.team.abbrv), db, current_user)
    db.delete(plan)
    db.commit()
    return result
