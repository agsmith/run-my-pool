"""Live NFL point-spread lookup and pool-specific lock snapshots."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import httpx
import models

ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"


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
