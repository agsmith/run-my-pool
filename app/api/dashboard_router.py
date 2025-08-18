import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.template_context import template_context
from app.middleware.authz import get_session, requires_permission
from app.services.role_service import Tab, Operation
from app.services.session_service import SessionData

templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    session: SessionData = Depends(get_session),
    is_auth: bool = Depends(requires_permission(Tab.DASHBOARD, Operation.VIEW))
):
    username = session.display_name
    role = session.role

    logger.info(f"rendering=dashboard, username={username} role={role}")
    return templates.TemplateResponse(
        "dashboard.html",
        template_context("dashboard", request, session)
    )
