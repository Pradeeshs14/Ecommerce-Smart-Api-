from fastapi import APIRouter, Request, HTTPException, Depends  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
import stripe  # type: ignore

from app.core.database import get_db
from app.core.config import STRIPE_WEBHOOK_SECRET
from app.models.payment import Payment
from app.models.order import Order


router = APIRouter(
    prefix="/payment",
    tags=["Payment"]
)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    # ========================================================
    # READ STRIPE WEBHOOK
    # ========================================================

    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    print("\n========== STRIPE WEBHOOK ==========")
    print("Payload received:", len(payload), "bytes")
    print("Signature received:", bool(signature))
    print("Webhook secret loaded:", bool(STRIPE_WEBHOOK_SECRET))

    # ========================================================
    # CHECK SIGNATURE
    # ========================================================

    if not signature:
        print("ERROR: Missing Stripe signature")

        raise HTTPException(
            status_code=400,
            detail="Missing Stripe signature"
        )

    # ========================================================
    # VERIFY STRIPE EVENT
    # ========================================================

    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            STRIPE_WEBHOOK_SECRET
        )

    except ValueError as exc:
        print("WEBHOOK PAYLOAD ERROR:", str(exc))

        raise HTTPException(
            status_code=400,
            detail="Invalid webhook payload"
        )

    except stripe.error.SignatureVerificationError as exc:
        print("WEBHOOK SIGNATURE ERROR:", str(exc))

        raise HTTPException(
            status_code=400,
            detail="Invalid Stripe signature"
        )

    # ========================================================
    # WEBHOOK VERIFIED
    # ========================================================

    event_type = event["type"]

    print("Webhook verified successfully")
    print("Event type:", event_type)

    # ========================================================
    # CHECKOUT SESSION COMPLETED
    # ========================================================

    if event_type == "checkout.session.completed":

        session = event["data"]["object"]

        # Stripe Session is a Stripe object, not a normal dict
        checkout_session_id = session.id

        print("\n====================================")
        print("CHECKOUT SESSION COMPLETED")
        print("Session ID:", checkout_session_id)
        print("====================================")

        if not checkout_session_id:
            print("ERROR: Checkout session ID missing")

            return {
                "status": "success"
            }

        try:
            # ------------------------------------------------
            # FIND PAYMENT
            # ------------------------------------------------

            payment = (
                db.query(Payment)
                .filter(
                    Payment.checkout_session_id
                    == checkout_session_id
                )
                .first()
            )

            print(
                "Payment found:",
                payment is not None
            )

            # ------------------------------------------------
            # PAYMENT NOT FOUND
            # ------------------------------------------------

            if not payment:
                print(
                    "WARNING: Payment record not found"
                )

                return {
                    "status": "success"
                }

            print(
                "Payment ID:",
                payment.id
            )

            print(
                "Order ID:",
                payment.order_id
            )

            print(
                "Current payment status:",
                payment.status
            )

            # ------------------------------------------------
            # UPDATE PAYMENT
            # ------------------------------------------------

            payment.status = "paid"

            print(
                "Payment status changed to PAID"
            )

            # ------------------------------------------------
            # FIND ORDER
            # ------------------------------------------------

            order = (
                db.query(Order)
                .filter(
                    Order.id == payment.order_id
                )
                .first()
            )

            print(
                "Order found:",
                order is not None
            )

            # ------------------------------------------------
            # UPDATE ORDER
            # ------------------------------------------------

            if order:

                print(
                    "Current order payment status:",
                    order.payment_status
                )

                order.payment_status = "paid"

                print(
                    "Order payment status changed to PAID"
                )

            else:

                print(
                    "WARNING: Order record not found"
                )

            # ------------------------------------------------
            # COMMIT DATABASE
            # ------------------------------------------------

            db.commit()

            print(
                "DATABASE COMMIT SUCCESS"
            )

            print(
                "Payment marked as PAID"
            )

            if order:
                print(
                    "Order marked as PAID"
                )

        except Exception as exc:

            db.rollback()

            print("\n====================================")
            print("WEBHOOK DATABASE ERROR")
            print("ERROR:", repr(exc))
            print("====================================")

            raise HTTPException(
                status_code=500,
                detail=f"Webhook database error: {str(exc)}"
            )

    # ========================================================
    # PAYMENT INTENT EVENTS
    # ========================================================

    elif event_type == "payment_intent.succeeded":

        print(
            "PaymentIntent succeeded"
        )

    elif event_type == "payment_intent.created":

        print(
            "PaymentIntent created"
        )

    # ========================================================
    # CHARGE EVENTS
    # ========================================================

    elif event_type == "charge.succeeded":

        print(
            "Charge succeeded"
        )

    elif event_type == "charge.updated":

        print(
            "Charge updated"
        )

    # ========================================================
    # OTHER EVENTS
    # ========================================================

    else:

        print(
            "Unhandled Stripe event:",
            event_type
        )

    # ========================================================
    # RESPONSE
    # ========================================================

    print(
        "Webhook processing completed successfully"
    )

    return {
        "status": "success"
    }