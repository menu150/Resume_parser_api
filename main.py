from fastapi import FastAPI, Request, Form, UploadFile, File, Header, HTTPException, Depends
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import stripe
import uuid
import os
import sqlite3
from parser import extract_text_from_pdf, parse_resume_text

# Initialize app and middleware
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="SUPERSECRET123")
templates = Jinja2Templates(directory="templates")

# Stripe config
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
PRICE_IDS = {
    "basic": os.getenv("STRIPE_PRICE_BASIC"),
    "pro": os.getenv("STRIPE_PRICE_PRO")
}

# Root
@app.get("/")
def root():
    return templates.TemplateResponse("index.html", {"request": {}})

# Create Stripe Checkout Session
@app.post("/create_checkout_session")
async def create_checkout_session(plan: str = Form(...)):
    if plan not in PRICE_IDS:
        return JSONResponse({"error": "Invalid plan"}, status_code=400)

    try:
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
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# Checkout Success Page
@app.get("/success", response_class=HTMLResponse)
async def checkout_success(request: Request):
    return templates.TemplateResponse("success.html", {"request": request})

# Checkout Cancel Page
@app.get("/cancel", response_class=HTMLResponse)
async def checkout_cancel(request: Request):
    return templates.TemplateResponse("cancel.html", {"request": request})
