# billing.py
import os
import stripe
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db import SessionLocal
from models import User, Subscription

router = APIRouter(prefix="/billing", tags=["billing"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
RETURN_URL = os.getenv("BILLING_PORTAL_RETURN_URL", "http://localhost:3000/dashboard/account")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

class CheckoutBody(BaseModel):
    email: str
    price_id: str  # e.g., STRIPE_PRICE_BASIC or STRIPE_PRICE_PRO

@router.post("/checkout")
def create_checkout(body: CheckoutBody, db: Session = Depends(get_db)):
    # ensure a local user row exists for this email
    user = db.query(User).filter(User.email == body.email).one_or_none()
    if not user:
        user = User(email=body.email)
        db.add(user)
        db.commit()
        db.refresh(user)

    # get or create stripe customer against this user
    # store customer on Subscription later via webhook, but we can precreate it:
    customer = stripe.Customer.create(email=body.email)

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": body.price_id, "quantity": 1}],
        customer=customer.id,
        success_url=f"{RETURN_URL}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{RETURN_URL}?cancelled=1",
        allow_promotion_codes=True,
    )

    # create a placeholder subscription row to attach in webhook
    sub = Subscription(
        user_id=user.id,
        stripe_customer_id=customer.id,
        status="incomplete"
    )
    db.add(sub); db.commit()

    return {"checkout_url": session.url}

class PortalBody(BaseModel):
    customer_id: str

@router.post("/portal")
def create_portal(body: PortalBody):
    try:
        portal = stripe.billing_portal.Session.create(
            customer=body.customer_id,
            return_url=RETURN_URL,
        )
        return {"portal_url": portal.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
