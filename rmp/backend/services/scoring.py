"""Atomic and idempotent scoring for Survivor and Pick 'Em pools."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import secrets
import uuid

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

import models
from services.nfl_results import NflGameResult


class ScoringDiscrepancy(RuntimeError):
    """A provider result cannot safely be reconciled with local data."""


MAX_SURVIVOR_MULLIGANS = 3


def _allowed_survivor_losses(pool: models.Pool) -> int:
    """Return a fail-safe allowance even if legacy or corrupted data bypasses validation."""
    return min(MAX_SURVIVOR_MULLIGANS, max(0, pool.survivor_mulligans or 0))


@dataclass
class ScoringSummary:
    final_games: int = 0
    games_changed: int = 0
    picks_changed: int = 0
    entries_changed: int = 0


def _winner_id(game: models.Schedule, result: NflGameResult) -> int | None:
    if result.is_tie:
        return None
    if result.home_score > result.away_score:
        return game.home_team_id
    return game.away_team_id


def _validate_match(game: models.Schedule, result: NflGameResult) -> None:
    if game.season != result.season or game.week_num != result.week:
        raise ScoringDiscrepancy(
            f"Game {result.game_id} season/week does not match local schedule"
        )
    local = {game.home_team.abbrv.upper(), game.away_team.abbrv.upper()}
    provider = {result.home_abbreviation, result.away_abbreviation}
    aliases = {"WAS": "WSH", "WSH": "WSH"}
    normalized_local = {aliases.get(value, value) for value in local}
    normalized_provider = {aliases.get(value, value) for value in provider}
    if normalized_local != normalized_provider:
        raise ScoringDiscrepancy(
            f"Game {result.game_id} teams do not match local schedule"
        )


def _reconcile_picks(
    db: Session,
    game: models.Schedule,
    winner_id: int | None,
) -> tuple[int, set[str]]:
    picks = (
        db.query(models.Pick)
        .join(models.Entry, models.Entry.id == models.Pick.entry_id)
        .join(models.Pool, models.Pool.id == models.Entry.pool_id)
        .filter(
            or_(
                and_(
                    models.Pool.pool_type == "pickem",
                    models.Pick.game_id == game.game_id,
                ),
                and_(
                    models.Pool.pool_type == "survivor",
                    models.Pick.week == game.week_num,
                    models.Pick.team_id.in_([game.home_team_id, game.away_team_id]),
                ),
            )
        )
        .all()
    )
    changed = 0
    affected_survivor_entries: set[str] = set()
    for pick in picks:
        # A final tie awards no Pick 'Em point and eliminates either Survivor pick.
        survived = winner_id is not None and pick.team_id == winner_id
        if (
            pick.entry.pool.pool_type == "survivor"
            and pick.entry.pool.survivor_objective == "lose"
        ):
            survived = winner_id is not None and pick.team_id != winner_id
        expected = "win" if survived else "loss"
        if pick.result != expected:
            pick.result = expected
            changed += 1
        if pick.entry.pool.pool_type == "survivor":
            affected_survivor_entries.add(pick.entry_id)
    return changed, affected_survivor_entries


def _reconcile_survivor_entries(db: Session, entry_ids: set[str]) -> int:
    if not entry_ids:
        return 0
    loss_counts = dict(
        db.query(models.Pick.entry_id, func.count(func.distinct(models.Pick.week)))
        .join(models.Entry, models.Entry.id == models.Pick.entry_id)
        .join(models.Pool, models.Pool.id == models.Entry.pool_id)
        .filter(models.Pick.entry_id.in_(entry_ids), models.Pick.result == "loss")
        .filter(models.Pool.pool_type == "survivor")
        .group_by(models.Pick.entry_id)
        .all()
    )
    changed = 0
    entries = (
        db.query(models.Entry)
        .options(joinedload(models.Entry.pool))
        .join(models.Pool, models.Pool.id == models.Entry.pool_id)
        .filter(models.Entry.id.in_(entry_ids))
        .filter(models.Pool.pool_type == "survivor")
        .all()
    )
    for entry in entries:
        allowed_losses = _allowed_survivor_losses(entry.pool)
        should_be_alive = loss_counts.get(entry.id, 0) <= allowed_losses
        if entry.alive != should_be_alive:
            entry.alive = should_be_alive
            changed += 1
    return changed


def apply_final_results(
    db: Session,
    results: list[NflGameResult],
    *,
    now: datetime | None = None,
) -> ScoringSummary:
    """Apply final results without committing; caller owns the transaction."""
    summary = ScoringSummary()
    affected_entries: set[str] = set()
    changed_at = (
        (now or datetime.now(timezone.utc))
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )

    final = [result for result in results if result.is_final]
    if not final:
        return summary
    if len({result.game_id for result in final}) != len(final):
        raise ScoringDiscrepancy("Provider response contains duplicate game IDs")

    games = (
        db.query(models.Schedule)
        .filter(models.Schedule.game_id.in_([result.game_id for result in final]))
        .all()
    )
    by_id = {game.game_id: game for game in games}
    missing = sorted({result.game_id for result in final} - set(by_id))
    if missing:
        raise ScoringDiscrepancy(f"Unknown provider game IDs: {missing}")

    for result in final:
        game = by_id[result.game_id]
        _validate_match(game, result)
        winner_id = _winner_id(game, result)
        changed = any(
            (
                game.status != "final",
                game.home_score != result.home_score,
                game.away_score != result.away_score,
                game.winning_team_id != winner_id,
            )
        )
        game.status = "final"
        game.home_score = result.home_score
        game.away_score = result.away_score
        game.winning_team_id = winner_id
        game.provider_updated_at = result.provider_updated_at
        if changed:
            game.result_updated_at = changed_at
            summary.games_changed += 1

        picks_changed, survivor_entries = _reconcile_picks(db, game, winner_id)
        summary.picks_changed += picks_changed
        affected_entries.update(survivor_entries)
        summary.final_games += 1

    db.flush()
    summary.entries_changed = _reconcile_survivor_entries(db, affected_entries)
    db.flush()
    return summary


def _reconcile_square_payouts(db: Session, game: models.Schedule, result: NflGameResult, changed_at: datetime) -> None:
    selected_pool_ids = db.query(models.PoolSquareGame.pool_id).filter(
        models.PoolSquareGame.game_id == game.game_id
    )
    pools = db.query(models.Pool).options(joinedload(models.Pool.square_board)).filter(
        models.Pool.pool_type == "squares",
        or_(models.Pool.id.in_(selected_pool_ids), models.Pool.squares_game_id == game.game_id),
    ).all()
    checkpoints = [
        ("q1", 1, result.home_q1_score, result.away_q1_score, "q1_percent"),
        ("halftime", 2, result.home_half_score, result.away_half_score, "halftime_percent"),
        ("q3", 3, result.home_q3_score, result.away_q3_score, "q3_percent"),
        ("final", 4, result.home_score, result.away_score, "final_percent"),
    ]
    for pool in pools:
        board = pool.square_board
        selected_game_count = len(pool.square_games) or 1
        total_pot_cents = board.total_pot_cents
        if board.pot_mode == "per_square" and board.per_square_cents is not None:
            claim_count = db.query(func.count(models.SquareClaim.id)).filter(
                models.SquareClaim.pool_id == pool.id,
            ).scalar() or 0
            total_pot_cents = board.per_square_cents * claim_count
        if not board.locked_at:
            generator = secrets.SystemRandom()
            board.home_digits = json.dumps(generator.sample(range(10), 10), separators=(",", ":"))
            board.away_digits = json.dumps(generator.sample(range(10), 10), separators=(",", ":"))
            board.locked_at = changed_at
            board.updated_at = changed_at
        home_digits, away_digits = json.loads(board.home_digits), json.loads(board.away_digits)
        for checkpoint, period, home_score, away_score, percent_field in checkpoints:
            if result.completed_period < period or home_score is None or away_score is None:
                continue
            row = home_digits.index(home_score % 10)
            column = away_digits.index(away_score % 10)
            claim = db.query(models.SquareClaim).filter(
                models.SquareClaim.pool_id == pool.id,
                models.SquareClaim.row_index == row,
                models.SquareClaim.column_index == column,
            ).first()
            payout = db.query(models.SquarePayout).filter(
                models.SquarePayout.pool_id == pool.id,
                models.SquarePayout.game_id == game.game_id,
                models.SquarePayout.checkpoint == checkpoint,
            ).first()
            if not payout:
                payout = models.SquarePayout(
                    id=str(uuid.uuid4()), pool_id=pool.id,
                    game_id=game.game_id, checkpoint=checkpoint,
                )
                db.add(payout)
            payout.home_score = home_score
            payout.away_score = away_score
            payout.winning_row = row
            payout.winning_column = column
            payout.winner_user_id = claim.user_id if claim else None
            payout.amount_cents = (
                round(total_pot_cents * getattr(board, percent_field) / 100 / selected_game_count)
                if total_pot_cents is not None else None
            )
            payout.determined_at = changed_at


def apply_game_results(db: Session, results: list[NflGameResult], *, now: datetime | None = None) -> ScoringSummary:
    """Persist live scores/checkpoints and apply final Survivor/Pick Em scoring."""
    changed_at = ((now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(tzinfo=None))
    if len({result.game_id for result in results}) != len(results):
        raise ScoringDiscrepancy("Provider response contains duplicate game IDs")
    if not results:
        return ScoringSummary()
    games = db.query(models.Schedule).filter(models.Schedule.game_id.in_([r.game_id for r in results])).all()
    by_id = {game.game_id: game for game in games}
    missing = sorted({result.game_id for result in results} - set(by_id))
    if missing:
        raise ScoringDiscrepancy(f"Unknown provider game IDs: {missing}")
    for result in results:
        game = by_id[result.game_id]
        _validate_match(game, result)
        game.status = result.status
        game.home_score = result.home_score
        game.away_score = result.away_score
        game.home_q1_score = result.home_q1_score if result.completed_period >= 1 else game.home_q1_score
        game.away_q1_score = result.away_q1_score if result.completed_period >= 1 else game.away_q1_score
        game.home_half_score = result.home_half_score if result.completed_period >= 2 else game.home_half_score
        game.away_half_score = result.away_half_score if result.completed_period >= 2 else game.away_half_score
        game.home_q3_score = result.home_q3_score if result.completed_period >= 3 else game.home_q3_score
        game.away_q3_score = result.away_q3_score if result.completed_period >= 3 else game.away_q3_score
        game.provider_updated_at = result.provider_updated_at
        _reconcile_square_payouts(db, game, result, changed_at)
    db.flush()
    final_summary = apply_final_results(db, results, now=now)
    return final_summary
