from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import sqlite3
import os
import stripe
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="templates")
DB_PATH = os.getenv("API_KEY_DB", "api_keys.db")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Login customer (email-based)
@router.get("/login_customer", response_class=HTMLResponse)
async def customer_login_form(request: Request):
    return templates.TemplateResponse("login_customer.html", {"request": request})

@router.post("/login_customer")
async def customer_login_submit(request: Request, email: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT key FROM api_keys WHERE email = ? LIMIT 1", (email,))
    row = cursor.fetchone()
    conn.close()

    if row:
        request.session["customer_email"] = email
        return RedirectResponse("/account", status_code=303)
    return templates.TemplateResponse("login_customer.html", {"request": request, "error": "No matching account found."})

# Customer dashboard
@router.get("/account", response_class=HTMLResponse)
async def customer_account(request: Request):
    email = request.session.get("customer_email")
    if not email:
        return RedirectResponse("/login_customer")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM api_keys WHERE email = ?", (email,))
    key_data = cursor.fetchone()
    conn.close()

    return templates.TemplateResponse("account.html", {
        "request": request,
        "key": key_data
    })

# Regenerate API key
@router.post("/regenerate_key")
async def regenerate_key(request: Request):
    email = request.session.get("customer_email")
    if not email:
        return RedirectResponse("/login_customer")

    new_key = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE api_keys SET key = ?, used = 0 WHERE email = ?", (new_key, email))
    conn.commit()
    conn.close()

    return RedirectResponse("/account", status_code=303)

# Stripe customer portal
@router.post("/customer_portal")
async def customer_portal(request: Request):
    email = request.session.get("customer_email")
    if not email:
        return RedirectResponse("/login_customer")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id FROM api_keys WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return RedirectResponse("/account")

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=row[0],
            return_url="http://localhost:8000/account"
        )
        return RedirectResponse(portal_session.url, status_code=303)
    except Exception as e:
        print("Error creating portal session:", e)
        return RedirectResponse("/account")

# Logout customer
@router.get("/logout_customer")
async def logout_customer(request: Request):
    request.session.clear()
    return RedirectResponse("/login_customer")
