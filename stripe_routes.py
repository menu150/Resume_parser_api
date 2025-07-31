# resume_parser_api/stripe_routes.py
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
import stripe
import os
import secrets
from database import api_keys  # adjust to your API key store

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@router.get("/buy")
async def buy():
    new_api_key = secrets.token_hex(16)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": os.getenv("STRIPE_PRICE_ID"),
            "quantity": 1,
        }],
        mode="subscription",
        success_url=f"{os.getenv('DOMAIN')}/success?api_key={new_api_key}&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{os.getenv('DOMAIN')}/cancel",
    )

    # Temporarily hold the key for assignment in webhook
    api_keys[new_api_key] = {"used": 0, "quota": 1000, "stripe_session": session.id}
    return RedirectResponse(session.url)
