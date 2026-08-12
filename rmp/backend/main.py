from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
import database
import routers
from sqlalchemy.orm import Session
import uvicorn
import os
import asyncio
import logging
import re
import time
import uuid
from contextlib import suppress
from weekly_locks import process_due_weekly_locks
from app_logging import configure_logging, log_event, request_id_context

configure_logging()
logger = logging.getLogger("runmypool.api")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")


def _request_id(request):
    supplied = request.headers.get("X-Request-ID", "")
    return supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid.uuid4())

# Skip SQLAlchemy table creation since schema is managed by datamodel.sql
# Database schema is managed by Alembic migrations.
# Run `alembic upgrade head` before starting the server to apply any pending migrations.

docs_enabled = os.getenv("ENABLE_API_DOCS", "0") == "1"
app = FastAPI(
    title="RunMyPool API",
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    request_id = _request_id(request)
    token = request_id_context.set(request_id)
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "http_request_failed",
            extra={
                "event": "http_request_failed",
                "method": request.method,
                "path": request.url.path,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            },
        )
        raise
    finally:
        request_id_context.reset(token)
    response.headers["X-Request-ID"] = request_id
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    if request.url.path.startswith("/auth/"):
        response.headers["Cache-Control"] = "no-store"
    log_event(
        logger,
        logging.WARNING if response.status_code >= 400 else logging.INFO,
        "http_request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round((time.monotonic() - started) * 1000, 2),
    )
    return response

# Get CORS origins from environment variable
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(routers.router)


async def _weekly_lock_worker():
    interval = max(int(os.getenv("WEEKLY_LOCK_SWEEP_INTERVAL_SECONDS", "60")), 15)
    while True:
        db = database.SessionLocal()
        try:
            process_due_weekly_locks(db)
        except Exception:
            db.rollback()
            logger.exception("weekly_lock_sweep_failed", extra={"event": "weekly_lock_sweep_failed"})
        finally:
            db.close()
        await asyncio.sleep(interval)


@app.on_event("startup")
async def start_weekly_lock_worker():
    if os.getenv("DISABLE_WEEKLY_LOCK_WORKER") == "1":
        return
    app.state.weekly_lock_task = asyncio.create_task(_weekly_lock_worker())


@app.on_event("shutdown")
async def stop_weekly_lock_worker():
    task = getattr(app.state, "weekly_lock_task", None)
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


@app.get("/")
def read_root():
    return {"message": "Welcome to the RunMyPool FastAPI backend!"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
