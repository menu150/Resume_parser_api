from fastapi import APIRouter, Request, HTTPException
import stripe
import os
from database import api_keys

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=endpoint_secret
        )
    except ValueError as e:
        print("Invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        print("Invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle event types
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session['id']
        customer_id = session['customer']
        subscription_id = session['subscription']

        # Assign session to an API key
        for key, data in api_keys.items():
            if data.get("stripe_session") == session_id:
                api_keys[key].update({
                    "customer_id": customer_id,
                    "subscription_id": subscription_id,
                    "stripe_session": None
                })
                print(f"Activated API key {key} for customer {customer_id}")
                break

    elif event['type'] == 'customer.subscription.deleted':
        customer_id = event['data']['object']['customer']
        # Disable API keys for this customer
        for key, data in api_keys.items():
            if data.get("customer_id") == customer_id:
                data["quota"] = 0
                print(f"Deactivated API key {key} for customer {customer_id}")
                break

    return {"status": "success"}
