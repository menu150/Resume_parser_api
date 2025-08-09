# main.py
import os
import time
from typing import Generator, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session

# Internal modules
from db import SessionLocal  # returns a session factory; see get_db() below
from models import User
from billing import router as billing_router
from stripe_webhooks import router as stripe_router

# --- App & Config -----------------------------------------------------------------

APP_ENV = os.getenv("APP_ENV", "development")
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]

app = FastAPI(
    title="ResumeParse API",
    description="Paid resume parsing API with Stripe billing, usage metering, and dashboard.",
    version="0.1.0",
)

# CORS (frontend <-> API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"] if APP_ENV != "production" else ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB Session Dependency ---------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    Yields a SQLAlchemy session per request.
    db.SessionLocal() (from our db.py) returns a session factory.
    """
    session_factory = SessionLocal()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()

# --- Basic Middleware: request id + security headers (lightweight) -----------------

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    # Tiny request id (for logs); feel free to expand to UUID
    rid = str(int(time.time() * 1000))
    response: JSONResponse
    try:
        response = await call_next(request)
    except Exception as e:
        # Ensure failures still include headers
        response = JSONResponse(
            {"error": "internal_error", "message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    response.headers["X-Request-Id"] = rid
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

# --- Health & Root -----------------------------------------------------------------

@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "ts": int(time.time()), "env": APP_ENV}

@app.get("/")
def root() -> dict:
    return {"name": "ResumeParse API", "status": "running"}

# --- (Optional) API-key Auth Dependency (stub for next step) -----------------------
# We’ll wire this up fully when we add metering on /api/parse.

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

    # TEMP flow until we wire real auth:
    # Fail closed so we don’t accidentally deploy unauthenticated.
    raise HTTPException(status_code=401, detail="API key auth not yet enabled")

# --- Example Parse Endpoint (wired later) ------------------------------------------
# Keep this commented OR guarded until auth+metering are ready.
#
# from parser import parse_resume  # your existing parser module
#
# @app.post("/api/parse")
# async def parse(file: UploadFile, user: User = Depends(get_current_user_from_api_key), db: Session = Depends(get_db)):
#     """
#     TODO:
#       - validate filetype/size
#       - call parse_resume(file)
#       - record UsageEvent + decrement MonthlyQuota in a transaction
#     """
#     ...

# --- Routers -----------------------------------------------------------------------

app.include_router(billing_router)       # /billing/checkout  /billing/portal
app.include_router(stripe_router)        # /stripe/webhook

# --- Error Handlers (nice JSON) ----------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exc_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exc_handler(_: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": str(exc) if APP_ENV != "production" else "unexpected error"},
    )
