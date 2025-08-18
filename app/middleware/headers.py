from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import MutableHeaders
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):
        logger.debug(f"Processing request: {request.url}")
        response = await call_next(request)
        self.set_security_headers(response.headers)
        logger.debug(f"Set security headers for: {request.url}")
        return response

    def set_security_headers(self, headers: MutableHeaders) -> None:
        headers["X-Frame-Options"] = "DENY"
        headers["X-Content-Type-Options"] = "nosniff"
        headers["Referrer-Policy"] = "no-referrer"
        headers["Content-Security-Policy"] = (
            "default-src 'self' https://ts3.comcast.com; "
            "style-src 'self' 'unsafe-inline' https://ts3.comcast.com; "
            "img-src 'self' data: https://ts3.comcast.com; "
            "script-src 'self' https://ts3.comcast.com; "
            "frame-src https://ts3.comcast.com; "
            "connect-src https://ts3.comcast.com"
        )
        headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
