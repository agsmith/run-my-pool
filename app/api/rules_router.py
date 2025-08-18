import os
import json
import bleach
import logging
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from app.services.mongo_service import MongoService
from app.services.role_service import RoleService, Tab, Operation
from app.services.csrf_service import CSRFService
from app.middleware.authz import get_session, requires_permission
from app.services.session_service import SessionData
from app.services.audit_service import AuditService

templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)
router = APIRouter()
db_service = MongoService()
csrf_service = CSRFService()
audit_service = AuditService(db_service)


@router.get("/rules/{rule_type}", response_class=HTMLResponse)
def rules_tab(request: Request, rule_type: str, session: SessionData = Depends(get_session),
              is_auth: bool = Depends(requires_permission(Tab.RULE, Operation.VIEW))):

    username = session.display_name
    role = session.role
    can_edit = RoleService.is_authorized(role, Tab.RULE, Operation.EDIT)
    can_add = RoleService.is_authorized(role, Tab.RULE, Operation.ADD)
    can_delete = RoleService.is_authorized(role, Tab.RULE, Operation.DELETE)
    is_viewer = not can_edit
    show_add_form = request.query_params.get("add") == "1" and can_add

    try:
        rules = list(db_service.get_db()[rule_type].find({}))
        logger.info(f"Fetched {len(rules)} rules for type: {rule_type}")
    except Exception as e:
        logger.exception(
            f"Exception while fetching rules for {rule_type}: {e}"
        )
        rules = []
        error_msg = (
            "Could not connect to the database. Please try again later."
        )
    else:
        error_msg = None

    all_keys = set()
    for rule in rules:
        all_keys.update(rule.keys())
    all_keys = sorted(all_keys)

    csrf_token = csrf_service.generate_csrf_token()

    response = templates.TemplateResponse(
        "rules.html",
        {
            "request": request,
            "tab": rule_type,
            "rules": rules,
            "headers": all_keys,
            "csrf_token": csrf_token,
            "username": username,
            "role": role,
            "error": error_msg,
            "show_add_form": show_add_form,
            "environment": os.getenv("ENV", "-"),
            "version": os.getenv("VERSION", "-"),
            "git_commit": os.getenv("GIT_COMMIT", "-")[:7],
            "active_section": "rules",
            "is_viewer": is_viewer,
            "user_role": role,
            "can_edit": can_edit,
            "can_add": can_add,
            "can_delete": can_delete
        }
    )
    csrf_service.set_csrf_cookie(response, csrf_token)
    logger.info(f"tab=rule, type={rule_type}, user={username} role={role})")
    return response


@router.post("/rules/{rule_type}/add", response_class=HTMLResponse)
async def add_rule(request: Request, rule_type: str, name: str = Form(...), code: str = Form(...), description: str = Form(""),
                   enable: str = Form(None), weight: float = Form(...), variable: str = Form(""), threshold: float = Form(...),
                   type: str = Form(...), csrf_token: str = Form(...), session: SessionData = Depends(get_session),
                   is_auth: bool = Depends(requires_permission(Tab.RULE, Operation.ADD))):

    await csrf_service.validate_csrf_token(request)

    if rule_type not in ["transaction_rules", "profile_rank", "profile_card"]:
        logger.warning(f"Rule type not found: {rule_type}")
        return HTMLResponse("Rule type not found", status_code=404)
    try:
        rule = {
            "name": bleach.clean(name),
            "code": bleach.clean(code),
            "description": bleach.clean(description),
            "enable": enable is not None,
            "weight": weight,
            "variable": bleach.clean(variable),
            "threshold": threshold,
            "type": type
        }
        result = db_service.get_db()[rule_type].insert_one(rule)
        if result.acknowledged:
            logger.info(f"Successfully added rule to {rule_type}: {rule}")
            audit_service.log_add_audit(session, rule)
    except Exception as e:
        logger.exception(f"Exception while adding rule to {rule_type}: {e}")
        rules = list(db_service.get_db()[rule_type].find({}, {"_id": 0}))
        csrf_token = csrf_service.generate_csrf_token()
        response = templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "tab": rule_type,
                "rules": rules,
                "error": "Invalid input.",
                "csrf_token": csrf_token
            }
        )
        csrf_service.set_csrf_cookie(response, csrf_token)
        return response
    return RedirectResponse(url=f"/rules/{rule_type}", status_code=302)


@router.post("/rules/{rule_type}/delete/{rule_id}", response_class=HTMLResponse)
async def delete_rule(
    request: Request,
    rule_type: str, rule_id: str,
    session: SessionData = Depends(get_session),
    is_auth: bool = Depends(requires_permission(Tab.RULE, Operation.DELETE))
):
    await csrf_service.validate_csrf_token(request)

    if rule_type not in ["transaction_rules", "profile_rank", "profile_card"]:
        logger.warning(f"Rule type not found: {rule_type}")
        return HTMLResponse("Rule type not found", status_code=404)
    try:
        rule_to_delete = db_service.get_db()[rule_type].find_one({"_id": ObjectId(rule_id)})
        db_service.get_db()[rule_type].delete_one({"_id": ObjectId(rule_id)})
        logger.info(f"Successfully deleted rule {rule_id} from {rule_type}")
        audit_service.log_delete_audit(session, rule_to_delete)
    except Exception as e:
        logger.exception(
            f"Exception while deleting rule {rule_id} from {rule_type}: {e}"
        )
    return RedirectResponse(url=f"/rules/{rule_type}", status_code=302)


@router.post("/rules/{rule_type}/edit/{rule_id}", response_class=HTMLResponse)
async def edit_rule(request: Request, rule_type: str, rule_id: str, session: SessionData = Depends(get_session),
                    is_auth: bool = Depends(requires_permission(Tab.RULE, Operation.ADD))):

    await csrf_service.validate_csrf_token(request)
    if rule_type not in ["transaction_rules", "profile_rank", "profile_card"]:
        logger.warning(f"Rule type not found: {rule_type}")
        return HTMLResponse("Rule type not found", status_code=404)
    form = await request.form()
    logger.info(f"Edit rule form payload: {dict(form)}")
    update_data = {}
    enable_present = False
    for k, v in form.items():
        if k in ["threshold", "weight"]:
            try:
                update_data[k] = float(v)
            except Exception:
                update_data[k] = v
        elif k == "enable":
            enable_present = True
            update_data[k] = v.lower() in ["true", "1", "on"]
        elif k == "variable":
            update_data[k] = bleach.clean(v)
        elif k == "description":
            update_data[k] = bleach.clean(v)
    if not enable_present:
        update_data["enable"] = False
    try:
        old_rule = db_service.get_db()[rule_type].find_one({"_id": ObjectId(rule_id)})
        db_service.get_db()[rule_type].update_one({"_id": ObjectId(rule_id)}, {"$set": update_data})
        logger.info(f"Successfully edited rule {rule_id} in {rule_type}: {update_data}")
        audit_service.log_edit_audit(session, {**old_rule, **update_data} if old_rule else update_data, old_rule)
    except Exception as e:
        logger.exception(f"Exception while editing rule {rule_id} in {rule_type}: {e}")
    return RedirectResponse(url=f"/rules/{rule_type}", status_code=302)


@router.get("/rules/{rule_type}/download")
def download_rules(
    request: Request,
    rule_type: str,
    session: SessionData = Depends(get_session),
    is_auth: bool = Depends(requires_permission(Tab.RULE, Operation.ADD))
):
    if rule_type not in ["transaction_rules", "profile_rank", "profile_card"]:
        return HTMLResponse("Rule type not found", status_code=404)
    try:
        rules = list(db_service.get_db()[rule_type].find({}))
        # Add 'id' field as string version of MongoDB _id
        for rule in rules:
            rule['id'] = str(rule['_id'])
            rule.pop('_id', None)
        content = json.dumps(rules, indent=2)
        from fastapi.responses import Response
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={rule_type}.json"}
        )
    except Exception as e:
        logger.exception(
            f"Exception while downloading rules for {rule_type}: {e}"
        )
        return HTMLResponse("Could not download rules.", status_code=500)
