import logging
import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

import schemas
from app_logging import log_event

logger = logging.getLogger("runmypool.lifecycle")
router = APIRouter(prefix="/analytics", tags=["analytics"])
MAX_EVENT_BYTES = 2_048
RATE_LIMIT = 120
RATE_WINDOW_SECONDS = 60
DEDUPLICATION_SECONDS = 10
_lock = threading.Lock()
_requests_by_client = defaultdict(deque)
_recent_events = {}


def _client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        # AWS ALB appends the address it observed, so the final value cannot be
        # replaced by a caller-supplied first value.
        return forwarded_for.rsplit(",", 1)[-1].strip()[:64]
    return (request.client.host if request.client else "unknown")[:64]


def _validate_content_length(
    content_length: str | None = Header(default=None, alias="Content-Length"),
):
    if content_length:
        try:
            if int(content_length) > MAX_EVENT_BYTES:
                raise HTTPException(
                    status_code=413, detail="Analytics event is too large"
                )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header")


def _enforce_limits(request: Request, event: schemas.LifecycleEvent) -> bool:
    now = time.monotonic()
    client = _client_key(request)
    fingerprint = (event.session_id, event.event, event.page, event.plan, event.source)
    with _lock:
        requests = _requests_by_client[client]
        while requests and requests[0] <= now - RATE_WINDOW_SECONDS:
            requests.popleft()
        if len(requests) >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Analytics rate limit exceeded")
        requests.append(now)

        if len(_recent_events) > 10_000:
            expired = [
                key
                for key, seen_at in _recent_events.items()
                if seen_at <= now - DEDUPLICATION_SECONDS
            ]
            for key in expired:
                _recent_events.pop(key, None)
        duplicate = _recent_events.get(fingerprint, 0) > now - DEDUPLICATION_SECONDS
        _recent_events[fingerprint] = now
        return duplicate


@router.post(
    "/events",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_validate_content_length)],
)
def record_lifecycle_event(event: schemas.LifecycleEvent, request: Request):
    """Write a privacy-safe customer lifecycle event to structured logs."""
    if _enforce_limits(request, event):
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    fields = event.model_dump(exclude_none=True)
    event_name = fields.pop("event")
    log_event(
        logger,
        logging.INFO,
        "customer_lifecycle_event",
        lifecycle_event=event_name,
        **fields,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
