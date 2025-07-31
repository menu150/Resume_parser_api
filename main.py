from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from parser import extract_text_from_pdf, parse_resume_text
from webhook import router as webhook_router
import stripe
import uuid
import os

# Basic Setup
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="SUPERSECRET123")
templates = Jinja2Templates(directory="templates")
app.include_router(webhook_router)

# Stripe Setup
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_123")

# API Key Management
API_KEYS = {
    "test-key-123": {"quota": 100, "used": 0, "customer_id": None},
    "demo-key-456": {"quota": 5, "used": 0, "customer_id": None}
}

UPLOAD_LOG = []

# Root
@app.get("/")
def root():
    return {"message": "Resume Parser API is live"}

# Parse Resume
@app.post("/parse_resume")
async def parse_resume(file: UploadFile = File(...), x_api_key: str = Header(...)):
    user = API_KEYS.get(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if user["used"] >= user["quota"]:
        raise HTTPException(status_code=429, detail="Quota exceeded")

    contents = await file.read()
    text = extract_text_from_pdf(contents)
    parsed = parse_resume_text(text)

    user["used"] += 1
    UPLOAD_LOG.append({"key": x_api_key, "filename": file.filename})
    return parsed

# Get Usage
@app.get("/usage")
def get_usage(x_api_key: str = Header(...)):
    user = API_KEYS.get(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"used": user["used"], "quota": user["quota"]}

# Stripe Checkout Session
@app.post("/create_checkout_session")
async def create_checkout_session(plan: str = Form(...)):
    try:
        price_id = {
            "basic": os.getenv("STRIPE_PRICE_BASIC", "price_123"),
            "pro": os.getenv("STRIPE_PRICE_PRO", "price_456")
        }.get(plan)

        if not price_id:
            raise HTTPException(status_code=400, detail="Invalid plan selected")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url='http://localhost:8000/dashboard?success=true',
            cancel_url='http://localhost:8000/dashboard?canceled=true',
        )
        return JSONResponse({"checkout_url": session.url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Reset Quota
@app.post("/reset_quota")
async def reset_quota(request: Request, key: str = Form(...)):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    if key in API_KEYS:
        API_KEYS[key]["used"] = 0
    return RedirectResponse(url="/dashboard", status_code=303)

# Regenerate Key
@app.post("/regenerate_key")
async def regenerate_key(request: Request, old_key: str = Form(...)):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login", status_code=303)
    if old_key in API_KEYS:
        API_KEYS[str(uuid.uuid4())] = API_KEYS.pop(old_key)
    return RedirectResponse(url="/dashboard", status_code=303)

# Dashboard
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse("/login")
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "api_keys": API_KEYS,
        "upload_log": UPLOAD_LOG
    })

# Login
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "admin123":
        request.session["logged_in"] = True
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid login"})

# Logout
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
