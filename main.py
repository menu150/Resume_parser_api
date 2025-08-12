"""
Directory: /
File: main.py
Purpose: FastAPI entrypoint for ResumeParse API — production‑ready defaults
- CORS (allow WP + app domains via ALLOWED_ORIGINS)
- Health checks (/health and /healthz)
- Security headers middleware with request ID
- DB session dependency
- Stripe + Billing routers inclusion
- Root → health redirect

ENV VARS (set in your host, not in git):
- APP_ENV: development|production (default: development)
- ALLOWED_ORIGINS: comma‑separated list, e.g. "https://YOUR-WP-DOMAIN.com,https://app.example.com"
"""

from __future__ import annotations

import os
import time
import logging
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

# Internal modules
from db import SessionLocal  # sessionmaker configured in db.py
from models import User
from billing import router as billing_router
from stripe_webhooks import router as stripe_router

# ----------------------------------------------------------------------------
# App & Config
# ----------------------------------------------------------------------------
APP_ENV = os.getenv("APP_ENV", "development").lower()
_allowed = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",") if o.strip()]
# In dev, allow * if nothing provided; in prod, require explicit origins
ALLOWED_ORIGINS = _allowed if _allowed else (["*"] if APP_ENV != "production" else [])

app = FastAPI(
    title="ResumeParse API",
    description="Paid resume parsing API with Stripe billing, usage metering, and dashboard.",
    version="0.1.0",
)

# ----------------------------------------------------------------------------
# CORS (frontend <-> API)
# ----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------------
# DB Session Dependency
# ----------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session per request."""
    db = SessionLocal()  # SessionLocal is a sessionmaker
    try:
        yield db
    finally:
        db.close()

# ----------------------------------------------------------------------------
# Basic Middleware: request id + security headers
# ----------------------------------------------------------------------------

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    rid = str(int(time.time() * 1000))  # simple millis request id
    try:
        response = await call_next(request)
    except Exception as e:
        response = JSONResponse(
            {"error": "internal_error", "message": str(e) if APP_ENV != "production" else "unexpected error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    response.headers["X-Request-Id"] = rid
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

# ----------------------------------------------------------------------------
# Health & Root
# ----------------------------------------------------------------------------

@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    return {"ok": True, "ts": int(time.time()), "env": APP_ENV}

@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok", "ts": int(time.time()), "env": APP_ENV}

@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/health", status_code=307)

# ----------------------------------------------------------------------------
# (Optional) API-key Auth Dependency (placeholder)
# ----------------------------------------------------------------------------

def get_current_user_from_api_key(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Placeholder for API key verification.
    Next step will:
      - read x-api-key header
      - hash-verify against ApiKey.key_hash
      - check active flag, rate limit, and monthly quota
      - return the associated User
    """
    api_key = request.headers.get("x-api-key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key")
    # Fail closed until implemented
    raise HTTPException(status_code=401, detail="API key auth not yet enabled")

# ----------------------------------------------------------------------------
# Routers
# ----------------------------------------------------------------------------

app.include_router(billing_router)  # e.g., /billing/checkout, /billing/portal
app.include_router(stripe_router)   # e.g., /webhooks/stripe (depends on router)

# ----------------------------------------------------------------------------
# Error Handlers (JSON)
# ----------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exc_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exc_handler(_: Request, exc: Exception):
    logging.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": str(exc) if APP_ENV != "production" else "unexpected error"},
    )
