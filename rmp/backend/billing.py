import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

import deps
import models
import schemas


router = APIRouter(prefix="/billing", tags=["billing"])

PLAN_DETAILS = {
    "commissioner": {"price_env": "STRIPE_PRICE_COMMISSIONER", "included_entries": 50, "max_pools": 1, "rank": 1},
    "pro": {"price_env": "STRIPE_PRICE_PRO", "included_entries": 150, "max_pools": 1, "rank": 2},
    "club": {"price_env": "STRIPE_PRICE_CLUB", "included_entries": 500, "max_pools": 5, "rank": 3},
    "club-unlimited": {"price_env": "STRIPE_PRICE_CLUB_UNLIMITED", "included_entries": None, "max_pools": None, "rank": 4},
}


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _stripe_value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _require_setting(name):
    value = os.getenv(name)
    if not value:
        raise HTTPException(status_code=503, detail="Commissioner payments are not configured yet")
    return value


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
    if _stripe_value(checkout_session, "payment_status") not in ("paid", "no_payment_required"):
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
    details = PLAN_DETAILS[order.plan]
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

    current_rank = PLAN_DETAILS.get(entitlement.plan, {}).get("rank", 0)
    if details["rank"] >= current_rank:
        entitlement.plan = order.plan
        entitlement.status = "active"
        entitlement.included_entries = details["included_entries"]
        entitlement.max_pools = details["max_pools"]
        entitlement.unlimited_entries = order.plan == "club-unlimited"
        entitlement.stripe_customer_id = order.stripe_customer_id
        entitlement.source_order_id = order.id
        entitlement.updated_at = now
    return order


@router.post("/checkout-session", response_model=schemas.CheckoutSessionOut)
def create_checkout_session(
    request: schemas.CheckoutSessionCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    plan = request.plan.strip().lower()
    details = PLAN_DETAILS.get(plan)
    if not details:
        raise HTTPException(status_code=400, detail="Unknown commissioner plan")

    existing = db.query(models.CommissionerEntitlement).filter(
        models.CommissionerEntitlement.user_id == current_user.id,
        models.CommissionerEntitlement.season == request.season,
        models.CommissionerEntitlement.status == "active",
    ).first()
    if existing and PLAN_DETAILS.get(existing.plan, {}).get("rank", 0) >= details["rank"]:
        raise HTTPException(status_code=409, detail=f"You already have {existing.plan} access for {request.season}")

    stripe.api_key = _require_setting("STRIPE_SECRET_KEY")
    price_id = _require_setting(details["price_env"])
    frontend_url = os.getenv("FRONTEND_URL", "https://runmypool.net").rstrip("/")
    now = _utcnow()
    order = models.BillingOrder(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        plan=plan,
        season=request.season,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db.add(order)
    db.commit()

    metadata = {"order_id": order.id, "user_id": current_user.id, "plan": plan, "season": str(request.season)}
    try:
        checkout = stripe.checkout.Session.create(
            mode="payment",
            customer_creation="always",
            customer_email=current_user.email,
            client_reference_id=current_user.id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_url}/pricing?checkout=cancelled",
            allow_promotion_codes=True,
            automatic_tax={"enabled": os.getenv("STRIPE_AUTOMATIC_TAX", "false").lower() == "true"},
            metadata=metadata,
            payment_intent_data={"metadata": metadata},
        )
    except stripe.StripeError as exc:
        order.status = "failed"
        order.updated_at = _utcnow()
        db.commit()
        raise HTTPException(status_code=502, detail="Unable to start secure checkout") from exc

    order.stripe_checkout_session_id = checkout.id
    order.updated_at = _utcnow()
    db.commit()
    return {"checkout_url": checkout.url, "session_id": checkout.id, "order_id": order.id}


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
    if db.query(models.StripeWebhookEvent).filter(models.StripeWebhookEvent.id == event_id).first():
        return {"received": True, "duplicate": True}

    checkout = _stripe_value(_stripe_value(event, "data"), "object")
    if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        try:
            fulfill_checkout(db, checkout)
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    elif event_type in ("checkout.session.expired", "checkout.session.async_payment_failed"):
        metadata = _stripe_value(checkout, "metadata", {}) or {}
        order = db.query(models.BillingOrder).filter(models.BillingOrder.id == metadata.get("order_id")).first()
        if order and order.status != "paid":
            order.status = "expired" if event_type.endswith("expired") else "failed"
            order.updated_at = _utcnow()

    db.add(models.StripeWebhookEvent(id=event_id, event_type=event_type, processed_at=_utcnow()))
    db.commit()
    return {"received": True}


@router.get("/status", response_model=Optional[schemas.CommissionerEntitlementOut])
def billing_status(
    season: int = Query(ge=2020, le=2100),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    return db.query(models.CommissionerEntitlement).filter(
        models.CommissionerEntitlement.user_id == current_user.id,
        models.CommissionerEntitlement.season == season,
        models.CommissionerEntitlement.status == "active",
    ).first()


@router.get("/session/{session_id}", response_model=schemas.BillingOrderOut)
def checkout_status(
    session_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    order = db.query(models.BillingOrder).filter(
        models.BillingOrder.stripe_checkout_session_id == session_id,
        models.BillingOrder.user_id == current_user.id,
    ).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkout session not found")
    return order
