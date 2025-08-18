from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import RedirectResponse
import logging
from app.services.session_service import session_store

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/auth/login",
            "/auth/azure-login",
            "/auth/azure-callback",
            "/static",
            "/health",
            "/logout",
            "/login"
        ]
        logger.info("Authentication middleware initialized")

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for excluded paths
        for path in self.exclude_paths:
            if request.url.path.startswith(path):
                return await call_next(request)

        # Check session
        try:
            session_id = request.cookies.get("session_id")
            if not session_id:
                logger.warning("No session_id cookie found")
                return RedirectResponse(url="/login", status_code=302)

            session_data = session_store.get_session(session_id)
            if not session_data:
                logger.warning(f"Invalid or expired session: {session_id[:8]}...")
                return RedirectResponse(url="/login", status_code=302)

            # Add session data to request state for use in route handlers
            request.state.session = session_data
            logger.info(f"Session validated for user: {session_data.display_name}")

            response = await call_next(request)
            return response
        except Exception as e:
            logger.exception(f"Authentication error: {str(e)}")
            return RedirectResponse(url="/login", status_code=302)
