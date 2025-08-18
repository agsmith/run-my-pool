from fastapi import Depends, Request, HTTPException
import logging
from app.models.session import SessionData
from app.services.role_service import RoleService, Tab, Operation

logger = logging.getLogger(__name__)


def get_session(request: Request) -> SessionData:
    if hasattr(request.state, 'session'):
        return request.state.session
    raise HTTPException(status_code=401, detail="Not authenticated")


def requires_permission(tab: Tab, operation: Operation):
    def permission_dependency(session: SessionData = Depends(get_session)) -> bool:
        is_allowed = RoleService.is_authorized(session.role, tab, operation)
        if not is_allowed:
            logger.warning(f"Access denied: user {session.display_name} with role {session.role} attempted {operation.name} on {tab.name}")
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return True
    return permission_dependency


def requires_admin(session: SessionData = Depends(get_session)) -> bool:
    if session.role.upper() != "ADMIN":
        logger.warning(f"Admin access denied for user with role {session.role}")
        raise HTTPException(status_code=403, detail="Admin access required")
    return True
