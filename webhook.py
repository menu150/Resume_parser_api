from fastapi import APIRouter, Request, Header, HTTPException
import stripe
import uuid
import os

router = APIRouter()

# Stripe API key setup
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_123")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test_123")

# Shared state for demo (use database in production)
from main import API_KEYS

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

    # Handle successful checkout
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_id = session.get("customer")
        email = session.get("customer_email")

        # Determine quota from plan (assume metadata or price lookup if needed)
        plan_quota = 100  # Default

        # Create and assign API key
        new_key = str(uuid.uuid4())
        API_KEYS[new_key] = {
            "quota": plan_quota,
            "used": 0,
            "customer_id": customer_id
        }

        print(f"✅ New API key issued: {new_key} for customer {email} ({customer_id})")

    return {"status": "success"}
