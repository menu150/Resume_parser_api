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
@app.post("/v1/parse/
