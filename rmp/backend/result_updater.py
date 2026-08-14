#!/usr/bin/env python3
"""Fetch and reconcile NFL results as a one-off container job."""

import argparse
import json
import logging
import os
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

import models
from database import SessionLocal, engine
from services.job_lock import advisory_job_lock
from services.nfl_results import fetch_scoreboard
from services.scoring import ScoringSummary, apply_game_results

LOGGER = logging.getLogger("runmypool.result_updater")
JOB_NAME = "nfl-results"
LOCK_NAME = "runmypool:nfl-results"


def _utc_naive(value: datetime | None = None) -> datetime:
    return (
        (value or datetime.now(timezone.utc))
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )


def configure_logging() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")


def log_event(event: str, **details) -> None:
    LOGGER.info(json.dumps({"event": event, **details}, sort_keys=True, default=str))


def candidate_contexts(
    db: Session,
    *,
    season: int | None = None,
    week: int | None = None,
    now: datetime | None = None,
    correction_hours: int = 72,
) -> list[tuple[int, int]]:
    if (season is None) != (week is None):
        raise ValueError("season and week must be supplied together")
    if season is not None:
        return [(season, week)]

    current = _utc_naive(now)
    games = (
        db.query(models.Schedule.season, models.Schedule.week_num)
        .filter(
            models.Schedule.start_time >= current - timedelta(hours=correction_hours),
            models.Schedule.start_time <= current + timedelta(hours=6),
        )
        .distinct()
        .all()
    )
    return sorted(set(games))


def create_run_record(
    db: Session,
    *,
    run_id: str,
    season: int | None,
    week: int | None,
    dry_run: bool,
) -> None:
    db.add(
        models.UpdaterRun(
            id=run_id,
            job_name=JOB_NAME,
            image_revision=os.getenv("IMAGE_REVISION"),
            season=season,
            week_num=week,
            source="espn",
            dry_run=dry_run,
            status="running",
            started_at=_utc_naive(),
        )
    )
    db.commit()


def finish_run_record(
    db: Session,
    run_id: str,
    *,
    status: str,
    games_fetched: int = 0,
    summary: ScoringSummary | None = None,
    error: str | None = None,
) -> None:
    record = db.get(models.UpdaterRun, run_id)
    if record is None:
        raise RuntimeError(f"Updater run record {run_id} disappeared")
    values = summary or ScoringSummary()
    record.status = status
    record.completed_at = _utc_naive()
    record.games_fetched = games_fetched
    record.final_games = values.final_games
    record.games_changed = values.games_changed
    record.picks_changed = values.picks_changed
    record.entries_changed = values.entries_changed
    record.summary = json.dumps(asdict(values), sort_keys=True)
    record.error = error
    db.commit()


def run_update(
    db: Session,
    *,
    run_id: str,
    season: int | None = None,
    week: int | None = None,
    dry_run: bool = False,
    correction_hours: int = 72,
) -> ScoringSummary:
    contexts = candidate_contexts(
        db,
        season=season,
        week=week,
        correction_hours=correction_hours,
    )
    if not contexts:
        summary = ScoringSummary()
        finish_run_record(db, run_id, status="no_games", summary=summary)
        return summary

    all_results = []
    for context_season, context_week in contexts:
        all_results.extend(fetch_scoreboard(context_season, context_week))

    summary = apply_game_results(db, all_results)
    if dry_run:
        db.rollback()
        status = "dry_run"
    else:
        db.commit()
        status = "succeeded"
    finish_run_record(
        db,
        run_id,
        status=status,
        games_fetched=len(all_results),
        summary=summary,
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int)
    parser.add_argument("--week", type=int)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--correction-hours", type=int, default=72)
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    if (args.season is None) != (args.week is None):
        raise SystemExit("--season and --week must be supplied together")
    run_id = args.run_id or str(uuid.uuid4())
    db = SessionLocal()
    try:
        create_run_record(
            db,
            run_id=run_id,
            season=args.season,
            week=args.week,
            dry_run=args.dry_run,
        )
        with advisory_job_lock(engine, LOCK_NAME) as acquired:
            if not acquired:
                finish_run_record(db, run_id, status="lock_skipped")
                log_event("lock_skipped", run_id=run_id)
                return 0
            summary = run_update(
                db,
                run_id=run_id,
                season=args.season,
                week=args.week,
                dry_run=args.dry_run,
                correction_hours=args.correction_hours,
            )
        log_event(
            "completed",
            run_id=run_id,
            status="dry_run" if args.dry_run else "succeeded",
            **asdict(summary),
        )
        return 0
    except Exception as exc:
        db.rollback()
        try:
            finish_run_record(db, run_id, status="failed", error=str(exc))
        except Exception:
            LOGGER.exception("Unable to persist updater failure record")
        log_event("failed", run_id=run_id, error=str(exc))
        LOGGER.exception("NFL result updater failed")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
