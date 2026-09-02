"""Live NFL point-spread lookup and pool-specific lock snapshots."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import httpx
import models

ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"
LIVE_LINE_CACHE_TTL = timedelta(minutes=30)


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fetch_game_line(game, client=None):
    owns_client = client is None
    client = client or httpx.Client(timeout=5.0)
    try:
        response = client.get(ESPN_SUMMARY_URL, params={"event": game.game_id})
        response.raise_for_status()
        pickcenter = response.json().get("pickcenter") or []
        if not pickcenter:
            return None
        odds = pickcenter[0]
        home_odds = odds.get("homeTeamOdds") or {}
        away_odds = odds.get("awayTeamOdds") or {}
        favorite_team_id = None
        if home_odds.get("favorite"):
            favorite_team_id = game.home_team_id
        elif away_odds.get("favorite"):
            favorite_team_id = game.away_team_id
        return {
            "game_id": game.game_id,
            "favorite_team_id": favorite_team_id,
            "spread": abs(float(odds["spread"])) if odds.get("spread") is not None else None,
            "details": odds.get("details"),
            "provider": (odds.get("provider") or {}).get("name", "ESPN"),
            "updated_at": _utcnow(),
        }
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return None
    finally:
        if owns_client:
            client.close()


def fetch_week_lines(games):
    lines = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_game_line, game) for game in games]
        for future in as_completed(futures):
            line = future.result()
            if line:
                lines[line["game_id"]] = line
    return lines


def _cached_line(record):
    if (
        record.provider is None
        and record.spread is None
        and record.details is None
    ):
        return None
    return {
        "game_id": record.game_id,
        "favorite_team_id": record.favorite_team_id,
        "spread": record.spread,
        "details": record.details,
        "provider": record.provider,
        "updated_at": record.fetched_at,
    }


def get_cached_week_lines(db, games, now=None):
    """Return shared lines, lazily refreshing entries older than 30 minutes."""
    if not games:
        return {}
    now = now or _utcnow()
    game_by_id = {game.game_id: game for game in games}
    cached = {
        record.game_id: record
        for record in db.query(models.GameLineCache).filter(
            models.GameLineCache.game_id.in_(game_by_id)
        ).all()
    }
    cutoff = now - LIVE_LINE_CACHE_TTL
    refresh_ids = {
        game_id
        for game_id in game_by_id
        if game_id not in cached or cached[game_id].fetched_at <= cutoff
    }
    refresh_games = [game_by_id[game_id] for game_id in refresh_ids]
    if refresh_games:
        # Recheck existing rows under a database lock. If another ECS task
        # refreshed while this request was waiting, this request uses its data
        # instead of making a duplicate provider call.
        locked = db.query(models.GameLineCache).filter(
            models.GameLineCache.game_id.in_(refresh_ids)
        ).with_for_update().all()
        cached.update({record.game_id: record for record in locked})
        refresh_games = [
            game_by_id[game_id]
            for game_id in refresh_ids
            if game_id not in cached or cached[game_id].fetched_at <= cutoff
        ]
        refreshed = fetch_week_lines(refresh_games)
        for game in refresh_games:
            line = refreshed.get(game.game_id)
            existing = cached.get(game.game_id)
            # Preserve the last known line during a transient provider miss,
            # while still negative-caching games that do not have lines yet.
            values = (
                line
                or (_cached_line(existing) if existing else None)
                or {}
            )
            db.merge(
                models.GameLineCache(
                    game_id=game.game_id,
                    favorite_team_id=values.get("favorite_team_id"),
                    spread=values.get("spread"),
                    details=values.get("details"),
                    provider=values.get("provider"),
                    fetched_at=now,
                )
            )
        db.commit()
        cached = {
            record.game_id: record
            for record in db.query(models.GameLineCache).filter(
                models.GameLineCache.game_id.in_(game_by_id)
            ).all()
        }
    return {
        game_id: line
        for game_id, record in cached.items()
        if (line := _cached_line(record)) is not None
    }


def freeze_week_lines(db, pool_id, week, games, captured_at=None):
    captured_at = captured_at or _utcnow()
    live_lines = fetch_week_lines(games)
    snapshots = []
    for game in games:
        line = live_lines.get(game.game_id)
        if not line:
            continue
        snapshot = db.merge(models.PoolGameLine(
            pool_id=pool_id,
            game_id=game.game_id,
            week_num=week,
            favorite_team_id=line["favorite_team_id"],
            spread=line["spread"],
            details=line["details"],
            provider=line["provider"],
            captured_at=captured_at,
        ))
        snapshots.append(snapshot)
    db.flush()
    return snapshots
