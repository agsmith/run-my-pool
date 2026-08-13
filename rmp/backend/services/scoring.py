"""Atomic and idempotent scoring for Survivor and Pick 'Em pools."""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

import models
from services.nfl_results import NflGameResult


class ScoringDiscrepancy(RuntimeError):
    """A provider result cannot safely be reconciled with local data."""


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
        expected = (
            "win" if winner_id is not None and pick.team_id == winner_id else "loss"
        )
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
        db.query(models.Pick.entry_id, func.count(models.Pick.id))
        .filter(models.Pick.entry_id.in_(entry_ids), models.Pick.result == "loss")
        .group_by(models.Pick.entry_id)
        .all()
    )
    changed = 0
    entries = db.query(models.Entry).filter(models.Entry.id.in_(entry_ids)).all()
    for entry in entries:
        should_be_alive = loss_counts.get(entry.id, 0) == 0
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
