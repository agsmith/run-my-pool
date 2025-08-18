from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from app.services.event_service import EventService
from app.middleware.authz import get_session, requires_permission
from app.services.role_service import Tab, Operation
from app.services.session_service import SessionData

router = APIRouter()
templates = Jinja2Templates(directory="templates")
event_service = EventService()


@router.get("/event")
def event_page(
    request: Request,
    session: SessionData = Depends(get_session),
    is_auth: bool = Depends(requires_permission(Tab.EVENT, Operation.VIEW))
):

    customer_id = request.query_params.get("customerId")
    billing_arrangement_id = request.query_params.get("billingArrangementID")
    view = request.query_params.get("view", "timeline")

    view_dict = event_service.get_event_view_model(
        customer_id=customer_id,
        billing_arrangement_id=billing_arrangement_id,
        view=view,
        request=request
    )

    view_dict["request"] = request
    view_dict["role"] = session.role
    view_dict["username"] = session.display_name
    return templates.TemplateResponse("event.html", view_dict)
