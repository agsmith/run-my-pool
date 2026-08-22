import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

import deps
import entitlements
import models
import schemas

router = APIRouter(prefix="/billing", tags=["billing"])

PLAN_DETAILS = {
    "squares-plus": {
        "price_env": "STRIPE_PRICE_SQUARES_PLUS",
        "price_cents": 1000,
        "included_entries": 100,
        "max_pools": 1,
        "rank": 0.5,
    },
    "commissioner": {
        "price_env": "STRIPE_PRICE_COMMISSIONER",
        "price_cents": 3900,
        "included_entries": 50,
        "max_pools": 1,
        "rank": 1,
    },
    "pro": {
        "price_env": "STRIPE_PRICE_PRO",
        "price_cents": 7900,
        "included_entries": 150,
        "max_pools": 3,
        "rank": 2,
    },
    "club": {
        "price_env": "STRIPE_PRICE_CLUB",
        "price_cents": 12900,
        "included_entries": 500,
        "max_pools": 5,
        "rank": 3,
    },
    "club-unlimited": {
        "price_env": "STRIPE_PRICE_CLUB_UNLIMITED",
        "price_cents": 24900,
        "included_entries": None,
        "max_pools": None,
        "rank": 4,
    },
}
CLUB_ENTRY_BLOCK_PRICE_CENTS = 2500
CLUB_ENTRY_BLOCK_SIZE = 100


def _upgrade_allowed(current_plan: Optional[str], target_plan: str) -> bool:
    """Allow upward upgrades, with Unlimited available only from Club."""
    if not current_plan:
        return True
    if target_plan == "club-unlimited":
        return current_plan == "club"
    if target_plan == "squares-plus":
        return False
    return PLAN_DETAILS.get(target_plan, {}).get("rank", 0) > PLAN_DETAILS.get(
        current_plan, {}
    ).get("rank", 0)


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _stripe_value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _require_setting(name):
    value = os.getenv(name)
    if not value:
        raise HTTPException(
            status_code=503, detail="Commissioner payments are not configured yet"
        )
    return value


def _queue_billing_audit(db, *, action, details, user_id, entitlement_id, data):
    """Add an audit row without committing the surrounding webhook transaction."""
    db.add(
        models.AuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            action=action,
            details=json.dumps(
                {
                    "description": details,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "entity_type": "commissioner_entitlement",
                    "entity_id": entitlement_id,
                    "additional_data": data,
                }
            ),
            created_at=_utcnow(),
        )
    )


def fulfill_checkout(db: Session, checkout_session):
    """Mark an order paid and grant its entitlement exactly once."""
    metadata = _stripe_value(checkout_session, "metadata", {}) or {}
    order_id = metadata.get("order_id")
    if not order_id:
        raise ValueError("Checkout session is missing order metadata")

    order = (
        db.query(models.BillingOrder)
        .filter(models.BillingOrder.id == order_id)
        .with_for_update()
        .first()
    )
    if not order:
        raise ValueError("Unknown billing order")
    if _stripe_value(checkout_session, "payment_status") not in (
        "paid",
        "no_payment_required",
    ):
        return order
    if order.status == "paid":
        return order

    now = _utcnow()
    order.status = "paid"
    order.stripe_checkout_session_id = _stripe_value(checkout_session, "id")
    order.stripe_payment_intent_id = _stripe_value(checkout_session, "payment_intent")
    order.stripe_customer_id = _stripe_value(checkout_session, "customer")
    order.amount_total = _stripe_value(checkout_session, "amount_total")
    order.currency = _stripe_value(checkout_session, "currency")
    order.paid_at = order.paid_at or now
    order.updated_at = now

    entitlement = (
        db.query(models.CommissionerEntitlement)
        .filter(
            models.CommissionerEntitlement.user_id == order.user_id,
            models.CommissionerEntitlement.season == order.season,
        )
        .with_for_update()
        .first()
    )
    if order.order_type == "entry_blocks":
        if (
            not entitlement
            or entitlement.plan != "club"
            or entitlement.status != "active"
        ):
            raise ValueError("Club entry blocks require an active Club entitlement")
        entitlement.entry_block_count += order.quantity
        entitlement.included_entries = (
            PLAN_DETAILS["club"]["included_entries"]
            + entitlement.entry_block_count * CLUB_ENTRY_BLOCK_SIZE
        )
        entitlement.stripe_customer_id = order.stripe_customer_id
        entitlement.source_order_id = order.id
        entitlement.updated_at = now
        db.flush()
        _queue_billing_audit(
            db,
            action="BILLING_ENTRY_CAPACITY_ADDED",
            details=f"Added {order.quantity * CLUB_ENTRY_BLOCK_SIZE} Club entries for {order.season}",
            user_id=order.user_id,
            entitlement_id=entitlement.id,
            data={
                "blocks": order.quantity,
                "new_capacity": entitlement.included_entries,
            },
        )
        return order

    details = PLAN_DETAILS[order.plan]
    previous_plan = entitlement.plan if entitlement else None
    if not entitlement:
        entitlement = models.CommissionerEntitlement(
            id=str(uuid.uuid4()),
            user_id=order.user_id,
            season=order.season,
            plan=order.plan,
            status="active",
            source_order_id=order.id,
            activated_at=now,
            updated_at=now,
        )
        db.add(entitlement)

    if previous_plan == order.plan or _upgrade_allowed(previous_plan, order.plan):
        entitlement.plan = order.plan
        entitlement.status = "active"
        entitlement.included_entries = details["included_entries"]
        entitlement.max_pools = details["max_pools"]
        entitlement.unlimited_entries = order.plan == "club-unlimited"
        if order.plan != "club":
            entitlement.entry_block_count = 0
        entitlement.stripe_customer_id = order.stripe_customer_id
        entitlement.source_order_id = order.id
        entitlement.updated_at = now
        db.flush()
        entitlements.assign_owner_pools(db, entitlement)
        _queue_billing_audit(
            db,
            action="BILLING_PLAN_ACTIVATED",
            details=f"Activated {order.plan} plan for {order.season}",
            user_id=order.user_id,
            entitlement_id=entitlement.id,
            data={"previous_plan": previous_plan, "plan": order.plan},
        )
    return order


@router.post("/checkout-session", response_model=schemas.CheckoutSessionOut)
def create_checkout_session(
    request: schemas.CheckoutSessionCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    order_type = request.order_type.strip().lower()
    if order_type not in ("plan", "entry_blocks"):
        raise HTTPException(status_code=400, detail="Unknown billing order type")
    plan = (request.plan or "").strip().lower()
    if order_type == "entry_blocks":
        plan = "club-entry-block"
        details = None
    else:
        details = PLAN_DETAILS.get(plan)
    if order_type == "plan" and not details:
        raise HTTPException(status_code=400, detail="Unknown commissioner plan")

    existing = (
        db.query(models.CommissionerEntitlement)
        .filter(
            models.CommissionerEntitlement.user_id == current_user.id,
            models.CommissionerEntitlement.season == request.season,
            models.CommissionerEntitlement.status == "active",
        )
        .first()
    )
    if order_type == "entry_blocks" and (not existing or existing.plan != "club"):
        raise HTTPException(
            status_code=409,
            detail="Additional entry blocks are available only with an active Club plan",
        )
    if order_type == "plan" and existing and not _upgrade_allowed(existing.plan, plan):
        if plan == "club-unlimited" and existing.plan != "club-unlimited":
            raise HTTPException(
                status_code=409,
                detail="Club Unlimited can be purchased initially or as an upgrade from Club.",
            )
        raise HTTPException(
            status_code=409,
            detail=f"You already have {existing.plan} access for {request.season}",
        )

    stripe.api_key = _require_setting("STRIPE_SECRET_KEY")
    if order_type == "entry_blocks":
        line_items = [
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": CLUB_ENTRY_BLOCK_PRICE_CENTS,
                    "product_data": {
                        "name": f"Run My Pool Club +{CLUB_ENTRY_BLOCK_SIZE} entries ({request.season})"
                    },
                },
                "quantity": request.quantity,
            }
        ]
    elif existing:
        upgrade_amount = (
            details["price_cents"] - PLAN_DETAILS[existing.plan]["price_cents"]
        )
        line_items = [
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": upgrade_amount,
                    "product_data": {
                        "name": f"Run My Pool {existing.plan} to {plan} upgrade ({request.season})"
                    },
                },
                "quantity": 1,
            }
        ]
    else:
        line_items = [{"price": _require_setting(details["price_env"]), "quantity": 1}]
    frontend_url = os.getenv("FRONTEND_URL", "https://runmypool.net").rstrip("/")
    now = _utcnow()
    order = models.BillingOrder(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        plan=plan,
        order_type=order_type,
        quantity=request.quantity if order_type == "entry_blocks" else 1,
        season=request.season,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db.add(order)
    db.commit()

    metadata = {
        "order_id": order.id,
        "user_id": current_user.id,
        "plan": plan,
        "season": str(request.season),
        "order_type": order_type,
        "quantity": str(order.quantity),
    }
    plan_year_start, plan_year_end = entitlements.plan_year_bounds(request.season)
    plan_year_message = (
        f"Plan year: {plan_year_start.strftime('%B')} {plan_year_start.day}, "
        f"{plan_year_start.year} through {plan_year_end.strftime('%B')} "
        f"{plan_year_end.day}, {plan_year_end.year}."
    )
    try:
        checkout = stripe.checkout.Session.create(
            mode="payment",
            customer_creation="always",
            customer_email=current_user.email,
            client_reference_id=current_user.id,
            line_items=line_items,
            success_url=f"{frontend_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=(
                f"{frontend_url}/profile?checkout=cancelled"
                if order_type == "entry_blocks"
                else f"{frontend_url}/pricing?checkout=cancelled&plan={plan}"
            ),
            allow_promotion_codes=True,
            automatic_tax={
                "enabled": os.getenv("STRIPE_AUTOMATIC_TAX", "false").lower() == "true"
            },
            custom_text={"submit": {"message": plan_year_message}},
            metadata=metadata,
            payment_intent_data={"metadata": metadata},
        )
    except stripe.StripeError as exc:
        order.status = "failed"
        order.updated_at = _utcnow()
        db.commit()
        raise HTTPException(
            status_code=502, detail="Unable to start secure checkout"
        ) from exc

    order.stripe_checkout_session_id = checkout.id
    order.updated_at = _utcnow()
    db.commit()
    return {
        "checkout_url": checkout.url,
        "session_id": checkout.id,
        "order_id": order.id,
    }


@router.get("/success", include_in_schema=False)
def redirect_legacy_checkout_success(session_id: str = Query(..., min_length=1)):
    """Keep already-issued Stripe redirects working outside the API namespace."""
    frontend_url = os.getenv("FRONTEND_URL", "https://runmypool.net").rstrip("/")
    query = urlencode({"session_id": session_id})
    return RedirectResponse(
        url=f"{frontend_url}/checkout/success?{query}", status_code=307
    )


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(deps.get_db)):
    webhook_secret = _require_setting("STRIPE_WEBHOOK_SECRET")
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook") from exc

    event_id = _stripe_value(event, "id")
    event_type = _stripe_value(event, "type")
    if (
        db.query(models.StripeWebhookEvent)
        .filter(models.StripeWebhookEvent.id == event_id)
        .first()
    ):
        return {"received": True, "duplicate": True}

    checkout = _stripe_value(_stripe_value(event, "data"), "object")
    if event_type in (
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    ):
        try:
            fulfill_checkout(db, checkout)
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    elif event_type in (
        "checkout.session.expired",
        "checkout.session.async_payment_failed",
    ):
        metadata = _stripe_value(checkout, "metadata", {}) or {}
        order = (
            db.query(models.BillingOrder)
            .filter(models.BillingOrder.id == metadata.get("order_id"))
            .first()
        )
        if order and order.status != "paid":
            order.status = "expired" if event_type.endswith("expired") else "failed"
            order.updated_at = _utcnow()

    db.add(
        models.StripeWebhookEvent(
            id=event_id, event_type=event_type, processed_at=_utcnow()
        )
    )
    db.commit()
    return {"received": True}


@router.get("/status", response_model=Optional[schemas.CommissionerEntitlementOut])
def billing_status(
    season: int = Query(ge=2020, le=2100),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    return (
        db.query(models.CommissionerEntitlement)
        .filter(
            models.CommissionerEntitlement.user_id == current_user.id,
            models.CommissionerEntitlement.season == season,
            models.CommissionerEntitlement.status == "active",
        )
        .first()
    )


@router.get("/overview", response_model=schemas.BillingOverviewOut)
def billing_overview(
    season: int = Query(ge=2020, le=2100),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Return only the signed-in user's plan and payment history for a season."""
    entitlement = (
        db.query(models.CommissionerEntitlement)
        .filter(
            models.CommissionerEntitlement.user_id == current_user.id,
            models.CommissionerEntitlement.season == season,
            models.CommissionerEntitlement.status == "active",
        )
        .first()
    )
    orders = (
        db.query(models.BillingOrder)
        .filter(
            models.BillingOrder.user_id == current_user.id,
            models.BillingOrder.season == season,
        )
        .order_by(models.BillingOrder.created_at.desc())
        .limit(20)
        .all()
    )
    used_entries = 0
    used_pools = entitlements.pool_creations_used(db, current_user.id, season)
    can_create_pool = True
    available_pool_slots = max(entitlements.FREE_MAX_POOLS - used_pools, 0)
    can_create_pool = available_pool_slots > 0
    if entitlement:
        pool_ids = db.query(models.Pool.id).filter(
            models.Pool.billing_entitlement_id == entitlement.id
        )
        if entitlement.max_pools is not None:
            available_pool_slots = max(entitlement.max_pools - used_pools, 0)
            can_create_pool = available_pool_slots > 0
        else:
            available_pool_slots = None
            can_create_pool = True
        used_entries = (
            db.query(func.count(models.Entry.id))
            .filter(models.Entry.pool_id.in_(pool_ids))
            .scalar()
            or 0
        )
    plan_year_start, plan_year_end = entitlements.plan_year_bounds(season)
    return {
        "season": season,
        "plan_year_start": plan_year_start,
        "plan_year_end": plan_year_end,
        "entitlement": entitlement,
        "orders": orders,
        "used_entries": used_entries,
        "used_pools": used_pools,
        "pools_created": used_pools,
        "can_create_pool": can_create_pool,
        "available_pool_slots": available_pool_slots,
    }


@router.get("/session/{session_id}", response_model=schemas.BillingOrderOut)
def checkout_status(
    session_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    order = (
        db.query(models.BillingOrder)
        .filter(
            models.BillingOrder.stripe_checkout_session_id == session_id,
            models.BillingOrder.user_id == current_user.id,
        )
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Checkout session not found"
        )
    return order
