from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse

from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import os
import logging

# Import the routers
from app.api.rules_router import router as rules_router
from app.api.login_router import router as login_router
from app.api.dashboard_router import router as dashboard_router
from app.api.event_router import router as event_router
from app.middleware.auth import AuthenticationMiddleware
from app.middleware.headers import SecurityHeadersMiddleware

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == status.HTTP_403_FORBIDDEN:
        return templates.TemplateResponse(
            "home.html",
            {"request": request, "permission_error": exc.detail},
            status_code=exc.status_code
        )
    return HTMLResponse(
        content=f"<h1>{exc.status_code} Error</h1><p>{exc.detail}</p>",
        status_code=exc.status_code
    )


@app.get("/")
def home(request: Request):
    logger.info("Redirecting to /rules/transaction_rules from home")
    return RedirectResponse(
        url="/rules/transaction_rules",
        status_code=302
    )


@app.get("/login")
def login_redirect(request: Request):
    logger.info("Redirecting to /auth/login")
    return RedirectResponse(
        url="/auth/login",
        status_code=302
    )


@app.get("/logout")
def logout_redirect(request: Request):
    logger.info("Redirecting to /auth/logout")
    return RedirectResponse(
        url="/auth/logout",
        status_code=302
    )


@app.get("/health")
def health():
    logger.info("Health check endpoint called")
    commit = os.getenv("GIT_COMMIT", "unknown")
    version = os.getenv("VERSION", "unknown")
    environment = os.getenv("ENV", "unknown")
    return {
        "status": "ok",
        "commit": commit,
        "version": version,
        "environment": environment
    }


app.include_router(rules_router)
app.include_router(login_router)
app.include_router(dashboard_router)
app.include_router(event_router)
