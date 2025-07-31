from fastapi import APIRouter, Request, Header, HTTPException
import stripe
import uuid
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_123")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test_123")

DB_PATH = os.getenv("API_KEY_DB", "api_keys.db")

# Initialize SQLite DB if not exists
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

# Price-based quota mapping
PRICE_QUOTAS = {
    os.getenv("STRIPE_PRICE_BASIC", "price_basic_id"): 100,
    os.getenv("STRIPE_PRICE_PRO", "price_pro_id"): 1000
}

# Email API key to user
def send_api_key_email(email, api_key):
    sender = os.getenv("SMTP_SENDER", "no-reply@example.com")
    password = os.getenv("SMTP_PASSWORD", "examplepassword")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.example.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your Resume Parser API Key"
    msg["From"] = sender
    msg["To"] = email

    text = f"""
    Thank you for subscribing!

    Your API key: {api_key}

    You can use this key to access the Resume Parser API.
    """
    msg.attach(MIMEText(text, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, email, msg.as_string())
        print(f"📧 Email sent to {email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, endpoint_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_id = session.get("customer")
        email = session.get("customer_email")
        price_id = session.get("items", [{}])[0].get("price") or session.get("metadata", {}).get("price_id")

        quota = PRICE_QUOTAS.get(price_id, 100)
        new_key = str(uuid.uuid4())

        # Save to SQLite
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO api_keys (key, quota, used, customer_id, email)
                VALUES (?, ?, 0, ?, ?)
            """, (new_key, quota, customer_id, email))

        send_api_key_email(email, new_key)
        print(f"✅ API key {new_key} created for customer {email} with quota {quota}")

    return {"status": "success"}
