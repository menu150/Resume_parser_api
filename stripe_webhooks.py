import os, json
from fastapi import APIRouter, Request, HTTPException
from starlette.responses import JSONResponse
import stripe
stripe.api_key = os.getenv("STRIPE_API_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
router = APIRouter(prefix="/webhooks/stripe", tags=["stripe"])
@router.post("")
async def receive_webhook(request: Request) -> JSONResponse:
    payload_bytes = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    try:
        payload_str = payload_bytes.decode("utf-8")
        if WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload_str, sig_header, WEBHOOK_SECRET)
        else:
            event = stripe.Event.construct_from(json.loads(payload_str), stripe.api_key)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {e}")
    etype = event["type"]
    data = event["data"]["object"]
    try:
        if etype == "checkout.session.completed": handle_checkout_session_completed(data)
        elif etype == "invoice.paid": handle_invoice_paid(data)
        elif etype == "customer.subscription.updated": handle_subscription_updated(data)
        elif etype == "customer.subscription.deleted": handle_subscription_deleted(data)
    except Exception as e:
        print(f"[stripe_webhooks] handler error: {e}")
    return JSONResponse({"received": True})
def handle_checkout_session_completed(obj: dict): print("[stripe] checkout.session.completed", obj.get("id"))
def handle_invoice_paid(obj: dict): print("[stripe] invoice.paid", obj.get("id"))
def handle_subscription_updated(obj: dict): print("[stripe] customer.subscription.updated", obj.get("id"))
def handle_subscription_deleted(obj: dict): print("[stripe] customer.subscription.deleted", obj.get("id"))
