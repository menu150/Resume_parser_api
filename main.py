import os
import json
import hmac
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict

import stripe
from fastapi import FastAPI, Header, HTTPException, Depends, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import (
    create_engine, text, select, Column, Integer, String, DateTime, Boolean, ForeignKey
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

# -----------------------------
# Environment & Config
# -----------------------------
APP_ENV = os.getenv("APP_ENV", "local")
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")

SECRET_PEPPER = os.getenv("SECRET_PEPPER", "change_me")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

stripe.api_key = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# price_id -> monthly quota
PLAN_QUOTAS: Dict[str, int] = json.loads(os.getenv("PLAN_QUOTAS_JSON", "{}"))

# -----------------------------
# DB setup (SQLAlchemy 2.0)
# -----------------------------
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class APIKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    key_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class MonthlyQuota(Base):
    __tablename__ = "monthly_quotas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    used: Mapped[int] = mapped_column(Integer, default=0)

# -----------------------------
# FastAPI app & CORS
# -----------------------------
app = FastAPI(title="Resume Parse API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in ALLOWED_ORIGINS else ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Helpers
# -----------------------------
def month_floor(dt: datetime) -> datetime:
    dt = dt.astimezone(timezone.utc)
    return datetime(dt.year, dt.month, 1, tzinfo=timezone.utc)

def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256((raw_key + SECRET_PEPPER).encode("utf-8")).hexdigest()

def issue_api_key(db, user_id: int) -> str:
    """Create a new API key (returns plaintext for display once)."""
    raw = "rk_" + secrets.token_urlsafe(32)
    h = hash_api_key(raw)
    db.add(APIKey(user_id=user_id, key_hash=h, active=True))
    db.commit()
    return raw

def get_or_create_user(db, email: str, stripe_customer_id: Optional[str] = None) -> User:
    user = db.query(User).filter(User.email == email).one_or_none()
    if user:
        if stripe_customer_id and not user.stripe_customer_id:
            user.stripe_customer_id = stripe_customer_id
            db.commit()
        return user
    user = User(email=email, stripe_customer_id=stripe_customer_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_or_create_month_quota(db, user_id: int, desired_limit: Optional[int] = None) -> MonthlyQuota:
    start = month_floor(datetime.now(timezone.utc))
    mq = (
        db.query(MonthlyQuota)
        .filter(MonthlyQuota.user_id == user_id, MonthlyQuota.period_start == start)
        .one_or_none()
    )
    if mq:
        # If a plan changed (new limit), update the limit but keep 'used'
        if desired_limit and mq.limit != desired_limit:
            mq.limit = desired_limit
            db.commit()
        return mq
    # If no record yet, set limit (default to 0 if unknown)
    mq = MonthlyQuota(user_id=user_id, period_start=start, limit=desired_limit or 0, used=0)
    db.add(mq)
    db.commit()
    db.refresh(mq)
    return mq

def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")
    return x_api_key

def authenticate_and_decrement(db, raw_key: str, cost: int = 1) -> User:
    h = hash_api_key(raw_key)
    # Active key?
    k = db.query(APIKey).filter(APIKey.key_hash == h, APIKey.active == True).one_or_none()
    if not k:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    # Ensure monthly quota exists
    mq = get_or_create_month_quota(db, k.user_id)
    # Enforce limit
    if mq.used + cost > mq.limit:
        raise HTTPException(status_code=402, detail="Quota exceeded. Upgrade plan or wait for next cycle.")
    # Atomic increment
    mq.used = mq.used + cost
    db.commit()
    user = db.query(User).filter(User.id == k.user_id).one()
    return user

# -----------------------------
# Schemas
# -----------------------------
class ParseRequest(BaseModel):
    file_url: Optional[str] = None
    # In production you'd handle file uploads separately. This is a stub input.

class ParseResponse(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: Optional[list[str]] = None
    raw_text: Optional[str] = None

class UsageOut(BaseModel):
    period_start: datetime
    used: int
    limit: int

class CheckoutIn(BaseModel):
    email: EmailStr
    price_id: str
    success_url: str
    cancel_url: str

class RotateKeyIn(BaseModel):
    email: EmailStr

# -----------------------------
# Health
# -----------------------------
@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}

# -----------------------------
# API: Resume Parsing (stub)
# -----------------------------
@app.post("/v1/parse/resume", response_model=ParseResponse)
def parse_resume(payload: ParseRequest, x_api_key: str = Depends(require_api_key)):
    """
    This is a stub parser to validate the full quota→billing path.
    Replace the body with your actual parsing pipeline.
    Cost: 1 unit
    """
    with SessionLocal() as db:
        user = authenticate_and_decrement(db, x_api_key, cost=1)

    # Stub response
    return ParseResponse(
        name="Jane Doe",
        email="jane.doe@example.com",
        phone="+1 (555) 555-5555",
        skills=["Python", "FastAPI", "NLP"],
        raw_text="(stub) Parsed content from resume."
    )

# -----------------------------
# API: Usage (for dashboard)
# -----------------------------
@app.get("/v1/usage", response_model=UsageOut)
def get_usage(x_api_key: str = Depends(require_api_key)):
    with SessionLocal() as db:
        h = hash_api_key(x_api_key)
        k = db.query(APIKey).filter(APIKey.key_hash == h, APIKey.active == True).one_or_none()
        if not k:
            raise HTTPException(status_code=401, detail="Invalid key")
        mq = get_or_create_month_quota(db, k.user_id)
        return UsageOut(period_start=mq.period_start, used=mq.used, limit=mq.limit)

# -----------------------------
# Ops: Rotate API key (dashboard button)
# Guarded by ADMIN_TOKEN to keep it simple for now.
# -----------------------------
@app.post("/admin/api-keys/rotate")
def rotate_key(body: RotateKeyIn, authorization: Optional[str] = Header(default=None)):
    if not ADMIN_TOKEN or authorization != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(status_code=403, detail="Forbidden")
    with SessionLocal() as db:
        user = get_or_create_user(db, body.email)
        # Deactivate old keys
        db.query(APIKey).filter(APIKey.user_id == user.id, APIKey.active == True).update({"active": False})
        db.commit()
        # Issue new
        raw = issue_api_key(db, user.id)
    return {"api_key": raw, "message": "Store this securely; it will not be shown again."}

# -----------------------------
# Billing: Create Checkout Session
# Triggered from frontend dashboard (/pricing)
# -----------------------------
@app.post("/billing/create-checkout-session")
def create_checkout_session(data: CheckoutIn):
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    # Ensure user exists locally
    with SessionLocal() as db:
        user = get_or_create_user(db, data.email)

    try:
        # Create (or reuse) customer
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=data.email)
            with SessionLocal() as db:
                u = db.query(User).filter(User.id == user.id).first()
                u.stripe_customer_id = customer.id
                db.commit()
            customer_id = customer.id
        else:
            customer_id = user.stripe_customer_id

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": data.price_id, "quantity": 1}],
            success_url=data.success_url,
            cancel_url=data.cancel_url,
            allow_promotion_codes=True
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# -----------------------------
# Stripe Webhook
# - checkout.session.completed
# - customer.subscription.created/updated/deleted
# - invoice.payment_succeeded (quota refill safety)
# -----------------------------
@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=sig_header, secret=STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {e}")

    evt_type = event["type"]

    def set_quota_from_price(db, user_id: int, price_id: Optional[str]):
        if not price_id:
            return
        limit = PLAN_QUOTAS.get(price_id, 0)
        get_or_create_month_quota(db, user_id, desired_limit=limit)

    if evt_type == "checkout.session.completed":
        session_obj = event["data"]["object"]
        customer_id = session_obj.get("customer")
        email = session_obj.get("customer_details", {}).get("email")
        price_id = None
        if session_obj.get("mode") == "subscription":
            # Get the subscription to read the price
            sub_id = session_obj.get("subscription")
            if sub_id:
                sub = stripe.Subscription.retrieve(sub_id)
                if sub["items"]["data"]:
                    price_id = sub["items"]["data"][0]["price"]["id"]

        with SessionLocal() as db:
            user = get_or_create_user(db, email, stripe_customer_id=customer_id)
            # Provision API key if none exists
            has_key = db.query(APIKey).filter(APIKey.user_id == user.id, APIKey.active == True).count() > 0
            if not has_key:
                _ = issue_api_key(db, user.id)
            # Set/Update monthly quota
            set_quota_from_price(db, user.id, price_id)

    elif evt_type in ("customer.subscription.created", "customer.subscription.updated"):
        sub = event["data"]["object"]
        customer_id = sub.get("customer")
        price_id = None
        if sub["items"]["data"]:
            price_id = sub["items"]["data"][0]["price"]["id"]

        with SessionLocal() as db:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).one_or_none()
            if user:
                set_quota_from_price(db, user.id, price_id)

    elif evt_type == "customer.subscription.deleted":
        # Zero out limit but keep usage for record
        sub = event["data"]["object"]
        customer_id = sub.get("customer")
        with SessionLocal() as db:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).one_or_none()
            if user:
                mq = get_or_create_month_quota(db, user.id)
                mq.limit = 0
                db.commit()

    elif evt_type == "invoice.payment_succeeded":
        # Safety: when Stripe rolls into new period, ensure our current month limit matches plan
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")
        lines = invoice.get("lines", {}).get("data", [])
        price_id = None
        if lines:
            price = lines[0].get("price")
            if price:
                price_id = price.get("id")
        with SessionLocal() as db:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).one_or_none()
            if user:
                set_quota_from_price(db, user.id, price_id)

    return {"received": True}
