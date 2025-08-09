# stripe_webhooks.py
import os, time, secrets
import stripe
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from db import SessionLocal
from models import User, Subscription, ApiKey, MonthlyQuota
from security import hash_api_key

router = APIRouter(prefix="/stripe", tags=["stripe"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
PRICE_BASIC = os.getenv("STRIPE_PRICE_BASIC")
PRICE_PRO = os.getenv("STRIPE_PRICE_PRO")

PLAN_QUOTAS = {
    PRICE_BASIC: 2000,  # adjust to your plan
    PRICE_PRO: 10000,
}

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def _period_bounds_from_sub(sub) -> tuple[int,int]:
    # sub.current_period_end is a unix ts in Stripe
    end = int(sub["current_period_end"])
    start = end - 30*24*3600  # rough; ok for MVP (can fetch current_period_start via expand if needed)
    return start, end

@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    t = event["type"]

    if t == "checkout.session.completed":
        session = event["data"]["object"]
        customer_id = session.get("customer")
        # find local user by customer email (simplest MVP)
        customer = stripe.Customer.retrieve(customer_id)
        email = customer.get("email")

        user = db.query(User).filter(User.email == email).one_or_none()
        if not user:
            user = User(email=email); db.add(user); db.commit(); db.refresh(user)

        # attach or create subscription row
        stripe_sub_id = session.get("subscription")
        price_id = session["line_items"]["data"][0]["price"]["id"] if session.get("line_items") else None

        sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == stripe_sub_id).one_or_none()
        if not sub:
            sub = Subscription(
                user_id=user.id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=stripe_sub_id,
                price_id=price_id,
                status="active",
                current_period_end=int(time.time())+30*24*3600,  # temp; will update on invoice.succeeded
            ); db.add(sub); db.commit(); db.refresh(sub)

        # create API key (plaintext shown once)
        plaintext = secrets.token_urlsafe(32)
        key_hash = hash_api_key(plaintext)
        api_key = ApiKey(user_id=user.id, key_hash=key_hash, label="default")
        db.add(api_key); db.commit()

        # initial monthly quota
        quota_limit = PLAN_QUOTAS.get(price_id, 2000)
        start, end = int(time.time()), int(time.time()) + 30*24*3600
        db.add(MonthlyQuota(user_id=user.id, period_start=start, period_end=end, limit=quota_limit, used=0))
        db.commit()

        # Return the plaintext key in response (Stripe ignores, but useful in logs)
        return {"ok": True, "api_key": plaintext}

    elif t == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        # refill quota on new billing period
        sub_id = invoice.get("subscription")
        sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == sub_id).one_or_none()
        if sub:
            stripe_sub = stripe.Subscription.retrieve(sub_id)
            sub.status = stripe_sub.status
            sub.price_id = stripe_sub["items"]["data"][0]["price"]["id"]
            sub.current_period_end = int(stripe_sub["current_period_end"])
            db.add(sub)
            # create new monthly quota row
            start, end = _period_bounds_from_sub(stripe_sub)
            limit = PLAN_QUOTAS.get(sub.price_id, 2000)
            db.add(MonthlyQuota(user_id=sub.user_id, period_start=start, period_end=end, limit=limit, used=0))
            db.commit()
        return {"ok": True}

    elif t in ("customer.subscription.deleted", "customer.subscription.paused"):
        obj = event["data"]["object"]
        sub_id = obj.get("id")
        sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == sub_id).one_or_none()
        if sub:
            sub.status = "canceled"
            db.add(sub); db.commit()
        return {"ok": True}

    # default: acknowledge other events
    return {"ok": True, "ignored": t}
