"""Validated NFL result acquisition independent of persistence and scoring."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ESPN_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
)

_STATUS_MAP = {
    "STATUS_SCHEDULED": "scheduled",
    "STATUS_IN_PROGRESS": "in_progress",
    "STATUS_HALFTIME": "in_progress",
    "STATUS_END_PERIOD": "in_progress",
    "STATUS_FINAL": "final",
    "STATUS_FINAL_OVERTIME": "final",
    "STATUS_POSTPONED": "postponed",
    "STATUS_CANCELED": "canceled",
}


class ResultProviderError(RuntimeError):
    """The result provider failed or returned an unsafe payload."""


@dataclass(frozen=True)
class NflGameResult:
    game_id: int
    season: int
    week: int
    status: str
    home_abbreviation: str
    away_abbreviation: str
    home_score: int | None
    away_score: int | None
    provider_updated_at: datetime | None = None

    @property
    def is_final(self) -> bool:
        return self.status == "final"

    @property
    def is_tie(self) -> bool:
        return (
            self.is_final
            and self.home_score is not None
            and self.home_score == self.away_score
        )


def _parse_score(value: Any, *, final: bool) -> int | None:
    if value in (None, ""):
        if final:
            raise ResultProviderError("Final game is missing a score")
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ResultProviderError(f"Invalid score value: {value!r}") from exc


def _parse_provider_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ResultProviderError(f"Invalid provider timestamp: {value!r}") from exc
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def parse_scoreboard(
    payload: dict[str, Any], *, season: int, week: int
) -> list[NflGameResult]:
    """Parse ESPN scoreboard JSON and fail closed on malformed relevant events."""
    events = payload.get("events")
    if not isinstance(events, list):
        raise ResultProviderError("ESPN response does not contain an events list")

    results: list[NflGameResult] = []
    for event in events:
        try:
            game_id = int(event["id"])
            raw_status = event["status"]["type"]["name"]
            competitions = event["competitions"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ResultProviderError("ESPN event is missing required fields") from exc

        status = _STATUS_MAP.get(raw_status)
        if status is None:
            raise ResultProviderError(f"Unsupported ESPN game status: {raw_status}")
        if not isinstance(competitions, list) or len(competitions) != 1:
            raise ResultProviderError(
                f"Game {game_id} must have exactly one competition"
            )

        competitors = competitions[0].get("competitors")
        if not isinstance(competitors, list) or len(competitors) != 2:
            raise ResultProviderError(
                f"Game {game_id} must have exactly two competitors"
            )

        by_side: dict[str, dict[str, Any]] = {}
        for competitor in competitors:
            side = competitor.get("homeAway")
            if side not in {"home", "away"} or side in by_side:
                raise ResultProviderError(f"Game {game_id} has invalid home/away data")
            by_side[side] = competitor
        if set(by_side) != {"home", "away"}:
            raise ResultProviderError(f"Game {game_id} is missing a home or away team")

        try:
            home_abbr = str(by_side["home"]["team"]["abbreviation"]).upper()
            away_abbr = str(by_side["away"]["team"]["abbreviation"]).upper()
        except (KeyError, TypeError) as exc:
            raise ResultProviderError(
                f"Game {game_id} is missing a team abbreviation"
            ) from exc
        if not home_abbr or not away_abbr:
            raise ResultProviderError(f"Game {game_id} has an empty team abbreviation")

        final = status == "final"
        results.append(
            NflGameResult(
                game_id=game_id,
                season=season,
                week=week,
                status=status,
                home_abbreviation=home_abbr,
                away_abbreviation=away_abbr,
                home_score=_parse_score(by_side["home"].get("score"), final=final),
                away_score=_parse_score(by_side["away"].get("score"), final=final),
                provider_updated_at=_parse_provider_time(
                    event.get("status", {}).get("type", {}).get("lastUpdated")
                ),
            )
        )
    return results


def build_http_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session = requests.Session()
    session.headers.update({"User-Agent": "RunMyPool-results-updater/1.0"})
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_scoreboard(
    season: int,
    week: int,
    *,
    session: requests.Session | None = None,
    timeout: tuple[float, float] = (5.0, 15.0),
) -> list[NflGameResult]:
    client = session or build_http_session()
    try:
        response = client.get(
            ESPN_SCOREBOARD_URL,
            params={"week": week, "seasontype": 2, "year": season, "limit": 100},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ResultProviderError("Unable to retrieve valid ESPN results") from exc
    return parse_scoreboard(payload, season=season, week=week)


def final_results(results: Iterable[NflGameResult]) -> list[NflGameResult]:
    return [result for result in results if result.is_final]
