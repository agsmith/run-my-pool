from fastapi import Request, HTTPException, Response
from typing import Optional
import secrets
import os
import logging

logger = logging.getLogger(__name__)


class CSRFService():

    def generate_csrf_token(self) -> str:
        token = secrets.token_urlsafe(32)
        logger.debug("Generated CSRF token")
        return token

    def set_csrf_cookie(self, response: Response, token: str) -> None:
        response.set_cookie(
            key="csrf_token",
            value=token,
            httponly=True,
            secure=not os.getenv("DEBUG", "").lower() == "true",
            samesite="Strict"
        )
        logger.debug("Set CSRF cookie")

    def get_csrf_token(self, request: Request) -> Optional[str]:
        return request.cookies.get("csrf_token")

    async def validate_csrf_token(self, request: Request) -> None:
        cookie_token = request.cookies.get("csrf_token")
        form_token = request.headers.get("x-csrf-token")
        if not form_token and request.method == "POST":
            try:
                form_data = await request.form()
                form_token = form_data.get("csrf_token")
            except Exception as e:
                logger.warning(f"Could not parse form data for CSRF validation: {e}")
                pass
        if not form_token or not cookie_token or form_token != cookie_token:
            logger.warning("CSRF token missing or invalid")
            raise HTTPException(
                status_code=403,
                detail="CSRF token missing or invalid"
            )
        logger.info("CSRF token validated successfully")
