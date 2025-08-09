# models.py
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone
from db import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")

class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    # store only a hash (bcrypt). show the plaintext once, on creation.
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index("ix_api_keys_user_active", "user_id", "active"),
    )

class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    stripe_customer_id: Mapped[str] = mapped_column(String(120), nullable=False)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    price_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(60), default="incomplete", nullable=False)
    current_period_end: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # Unix ts

    user = relationship("User", back_populates="subscriptions")

    __table_args__ = (
        Index("ix_subscriptions_user_status", "user_id", "status"),
        UniqueConstraint("stripe_subscription_id", name="uq_stripe_subscription_id"),
    )

class MonthlyQuota(Base):
    __tablename__ = "monthly_quotas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    period_start: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Unix ts (start of billing period)
    period_end: Mapped[int] = mapped_column(BigInteger, nullable=False)    # Unix ts (end of billing period)
    limit: Mapped[int] = mapped_column(Integer, nullable=False)            # allowed units
    used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_quotas_user_period", "user_id", "period_start", "period_end"),
    )

class UsageEvent(Base):
    __tablename__ = "usage_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id", ondelete="SET NULL"), index=True, nullable=True)
    ts: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Unix ts
    units: Mapped[int] = mapped_column(Integer, nullable=False)  # e.g., 1 per parse
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_usage_user_ts", "user_id", "ts"),
    )
