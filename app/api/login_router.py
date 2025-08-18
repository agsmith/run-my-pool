import os
import logging
import jwt
from typing import Optional
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.msal_auth_service import MSALAuthService
from app.services.csrf_service import CSRFService
from app.services.session_service import session_store
from app.models.session import SessionData

# Define role constants
ADMIN_ROLE = "516c4060-4805-428d-a5b8-092ebbd5ef12_admin"
VIEWER_ROLE = "516c4060-4805-428d-a5b8-092ebbd5ef12_viewer"
BUSINESS_ROLE = "516c4060-4805-428d-a5b8-092ebbd5ef12_business"

router = APIRouter(prefix="/auth")
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)
msal_auth_service = MSALAuthService()
csrf_service = CSRFService()


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    csrf_token = csrf_service.generate_csrf_token()
    response = templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": None,
            "csrf_token": csrf_token,
            "git_commit": os.getenv("GIT_COMMIT", "unknown")[:7],
            "version": os.getenv("VERSION", "unknown"),
            "environment": os.getenv("ENV", "unknown")
        }
    )
    csrf_service.set_csrf_cookie(response, csrf_token)
    logger.info(f"form=login, client={request.client.host}")
    return response


@router.post("/login", response_class=HTMLResponse)
def login(request: Request, response: Response):
    logger.info("endpoint=/login - redirecting=/auth/azure-login")
    return RedirectResponse(url="/auth/azure-login", status_code=302)


@router.get("/logout")
def logout(request: Request):
    username = request.cookies.get("username", "Unknown user")
    logger.info(f"User logged out: {username}")
    response = RedirectResponse(url="/auth/login", status_code=302)
    clear_auth_cookies(response, request)
    return response


@router.get("/azure-login")
def azure_login(request: Request):
    try:
        state = os.urandom(16).hex()
        auth_url = msal_auth_service.get_auth_url(state)
        response = RedirectResponse(url=auth_url)
        response.set_cookie(
            key="azure_state",
            value=state,
            httponly=True,
            max_age=3600
        )
        logger.info(f"Redirecting to Azure AD login with state: {state}")
        return response
    except Exception as e:
        logger.error(f"Azure login error: {str(e)}")
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Azure AD configuration error. Check server logs."
            }
        )


@router.get("/azure-callback")
def azure_callback(request: Request, code: str = None, state: str = None, error: str = None,
                   error_desc: str = None):
    if error:
        return redirect_login(request, 400, f"Azure AD authentication error: {error} error_desc: {error_desc}")

    saved_state = request.cookies.get("azure_state")
    if not saved_state or state != saved_state:
        return redirect_login(request, 400, "State mismatch: rcvd={state}, saved={saved_state}")

    if not code:
        return redirect_login(request, 400, "No authorization code provided")

    try:
        token_response = msal_auth_service.get_token_from_code(code)
        id_token = token_response.get("id_token")
        logger.info("Validating ID token")
        try:
            claims = msal_auth_service.validate_token(id_token)
        except jwt.jwt.InvalidTokenError as e:
            error_msg = e.__cause__
            logger.warning(f"Invalid Azure AD token: {error_msg}")
            return redirect_login(request, 401, f"Invalid token: {error_msg}")

        logger.info("ID token validation successful")
        response = RedirectResponse(
            url="/rules/transaction_rules",
            status_code=302
        )

        set_auth_cookies(response, claims)
        logger.info("Redirecting to rules page")
        return response

    except Exception as e:
        logger.error(f"Azure AD authentication error: {str(e)}")
        return redirect_login(request, 500, f"Authentication error: {str(e)}")


def redirect_login(request, err_code, message):
    logger.error(f"redirecting=login, error_code={err_code}, message={message}")
    return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": message
            },
            status_code=err_code
        )


def set_auth_cookies(response: Response, claims) -> None:
    username = claims.get("preferred_username")
    session = SessionData(
        username=username,
        role=claims.get("roles")[0],
        mail=claims.get("mail"),
        display_name=claims.get("name"))
    session_id = session_store.create_session(session)

    response.set_cookie(key="session_id", value=session_id, path="/",
                        httponly=True, secure=True, samesite="Lax", max_age=86400)
    logger.info(f"Created server-side session for user: {username}")


def clear_auth_cookies(response: Response, request: Optional[Request] = None) -> None:
    if request:
        session_id = request.cookies.get("session_id")
        if session_id:
            session_store.delete_session(session_id)
            logger.debug(f"Deleted session {session_id[:8]}... from store")
    response.delete_cookie("session_id")
    response.delete_cookie("csrf_token")
    logger.debug("Cleared auth cookies")
