from fastapi import FastAPI, Request, Form, UploadFile, File, Header, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import stripe
import uuid
import os
import sqlite3
from parser import extract_text_from_pdf, parse_resume_text

# FastAPI setup
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="SUPERSECRET123")
templates = Jinja2Templates(directory="templates")

# Stripe config
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
PRICE_IDS = {
    "basic": os.getenv("STRIPE_PRICE_BASIC"),
    "pro": os.getenv("STRIPE_PRICE_PRO")
}

DB_PATH = os.getenv("API_KEY_DB", "api_keys.db")

# Initialize DB
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                key TEXT PRIMARY KEY,
                quota INTEGER,
                used INTEGER DEFAULT 0,
                customer_id TEXT,
                email TEXT
            )
        ''')

init_db()

# Home
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Checkout
@app.post("/create_checkout_session")
async def create_checkout_session(plan: str = Form(...)):
    if plan not in PRICE_IDS:
        return JSONResponse({"error": "Invalid plan"}, status_code=400)

    session = stripe.checkout.Session.create(
        success_url="http://localhost:8000/success",
        cancel_url="http://localhost:8000/cancel",
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{
            "price": PRICE_IDS[plan],
            "quantity": 1
        }],
        metadata={"plan": plan}
    )
    return RedirectResponse(session.url, status_code=303)

# Customer portal session
@app.post("/create_customer_portal_session")
async def create_customer_portal_session(email: str = Form(...)):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT customer_id FROM api_keys WHERE email = ? LIMIT 1", (email,))
        row = cursor.fetchone()

    if not row:
        return JSONResponse({"error": "Customer not found"}, status_code=404)

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=row[0],
            return_url="http://localhost:8000/dashboard"
        )
        return RedirectResponse(portal_session.url, status_code=303)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# Dashboard
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    keys = conn.execute("SELECT * FROM api_keys").fetchall()
    conn.close()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "keys": keys
    })

# Login
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "admin123":
        request.session["logged_in"] = True
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid login"})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")

# Success and Cancel Pages
@app.get("/success", response_class=HTMLResponse)
async def checkout_success(request: Request):
    return templates.TemplateResponse("success.html", {"request": request})

@app.get("/cancel", response_class=HTMLResponse)
async def checkout_cancel(request: Request):
    return templates.TemplateResponse("cancel.html", {"request": request})
