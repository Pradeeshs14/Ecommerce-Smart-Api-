
from fastapi import APIRouter, Request, HTTPException, Depends  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

import stripe  # type: ignore

from app.core.database import get_db
from app.core.config import STRIPE_WEBHOOK_SECRET
from app.core.email import send_email

from app.models.payment import Payment
from app.models.order import Order
from app.models.user import User
from app.models.notification import Notification

from app.services.websocket_manager import manager


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/payment",
    tags=["Payment"]
)


# ============================================================
# STRIPE WEBHOOK
# ============================================================

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):

    # ========================================================
    # READ STRIPE WEBHOOK
    # ========================================================

    payload = await request.body()

    signature = request.headers.get(
        "stripe-signature"
    )

    print("\n========== STRIPE WEBHOOK ==========")

    print(
        "Payload received:",
        len(payload),
        "bytes"
    )

    print(
        "Signature received:",
        bool(signature)
    )

    print(
        "Webhook secret loaded:",
        bool(STRIPE_WEBHOOK_SECRET)
    )


    # ========================================================
    # CHECK SIGNATURE
    # ========================================================

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing Stripe signature"
        )

    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Stripe webhook secret is not configured"
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

        print(
            "WEBHOOK PAYLOAD ERROR:",
            str(exc)
        )

        raise HTTPException(
            status_code=400,
            detail="Invalid webhook payload"
        )

    except stripe.error.SignatureVerificationError as exc:

        print(
            "WEBHOOK SIGNATURE ERROR:",
            str(exc)
        )

        raise HTTPException(
            status_code=400,
            detail="Invalid Stripe signature"
        )


    # ========================================================
    # EVENT VERIFIED
    # ========================================================

    event_type = event["type"]

    print(
        "Webhook verified successfully"
    )

    print(
        "Event type:",
        event_type
    )


    # ========================================================
    # CHECKOUT SESSION COMPLETED
    # ========================================================

    if event_type == "checkout.session.completed":

        session = event["data"]["object"]

        checkout_session_id = session["id"]

        print("\n====================================")
        print("CHECKOUT SESSION COMPLETED")
        print(
            "Session ID:",
            checkout_session_id
        )
        print("====================================")


        try:

            # ==================================================
            # FIND PAYMENT
            # ==================================================

            payment = (
                db.query(Payment)
                .filter(
                    Payment.checkout_session_id
                    == checkout_session_id
                )
                .first()
            )


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
                "Current payment status:",
                payment.status
            )


            # ==================================================
            # IDEMPOTENCY CHECK
            # ==================================================

            if payment.status == "paid":

                print(
                    "Payment already marked as PAID"
                )

                return {
                    "status": "success",
                    "message": "Payment already processed"
                }


            # ==================================================
            # FIND ORDER
            # ==================================================

            order = (
                db.query(Order)
                .filter(
                    Order.id == payment.order_id
                )
                .first()
            )


            if not order:

                print(
                    "WARNING: Order not found"
                )

                return {
                    "status": "success"
                }


            print(
                "Order ID:",
                order.id
            )


            # ==================================================
            # FIND USER
            # ==================================================

            user = (
                db.query(User)
                .filter(
                    User.id == order.user_id
                )
                .first()
            )


            if not user:

                print(
                    "WARNING: User not found"
                )

                return {
                    "status": "success"
                }


            print(
                "Customer email:",
                user.email
            )


            # ==================================================
            # UPDATE PAYMENT
            # ==================================================

            print(
                "DEBUG 1: Before reading payment_intent"
            )


            payment_intent_id = session.payment_intent


            print(
                "DEBUG 2: PaymentIntent ID:",
                payment_intent_id
            )


            if payment_intent_id:

                payment.payment_intent_id = (
                    payment_intent_id
                )

                print(
                    "DEBUG 3: payment_intent_id assigned"
                )

                payment.transaction_id = (
                    payment_intent_id
                )

                print(
                    "DEBUG 4: transaction_id assigned"
                )

            else:

                print(
                    "WARNING: PaymentIntent ID not available in Checkout Session"
                )


            payment.status = "paid"


            print(
                "DEBUG 5: payment status assigned"
            )


            # ==================================================
            # UPDATE ORDER
            # ==================================================

            order.payment_status = "paid"

            order.status = "confirmed"


            print(
                "Order object updated"
            )


            # ==================================================
            # CREATE PAYMENT SUCCESS NOTIFICATION
            # ==================================================

            payment_notification = Notification(

                user_id=user.id,

                type="payment_success",

                message=(
                    f"Payment successful for "
                    f"Order #{order.id}"
                ),

                read_status="unread"
            )


            db.add(
                payment_notification
            )


            # ==================================================
            # CREATE ORDER CONFIRMED NOTIFICATION
            # ==================================================

            order_notification = Notification(

                user_id=user.id,

                type="order_confirmed",

                message=(
                    f"Your Order #{order.id} "
                    f"has been confirmed"
                ),

                read_status="unread"
            )


            db.add(
                order_notification
            )


            # ==================================================
            # COMMIT DATABASE CHANGES
            # ==================================================

            db.commit()


            print(
                "Payment status updated to PAID"
            )

            print(
                "Order payment status updated to PAID"
            )

            print(
                "Order status updated to CONFIRMED"
            )

            print(
                "Payment success notification created"
            )

            print(
                "Order confirmation notification created"
            )


            # ==================================================
            # REAL-TIME PAYMENT NOTIFICATION
            # ==================================================

            try:

                await manager.send_to_user(

                    user.id,

                    {
                        "event": "payment_success",

                        "order_id": order.id,

                        "payment_id": payment.id,

                        "payment_status": "paid",

                        "message": (
                            f"Payment successful for "
                            f"Order #{order.id}"
                        )
                    }
                )


                print(
                    "Real-time payment notification sent"
                )


            except Exception as websocket_exc:

                print(
                    "WEBSOCKET PAYMENT ERROR:",
                    repr(websocket_exc)
                )


            # ==================================================
            # REAL-TIME ORDER UPDATE
            # ==================================================

            try:

                await manager.send_to_user(

                    user.id,

                    {
                        "event":
                        "order_status_updated",

                        "order_id":
                        order.id,

                        "status":
                        "confirmed",

                        "payment_status":
                        "paid",

                        "message": (
                            f"Your Order #{order.id} "
                            f"has been confirmed"
                        )
                    }
                )


                print(
                    "Real-time order notification sent"
                )


            except Exception as websocket_exc:

                print(
                    "WEBSOCKET ORDER ERROR:",
                    repr(websocket_exc)
                )


            # ==================================================
            # SEND ORDER PLACED + PAYMENT CONFIRMED EMAIL
            # ==================================================

            try:

                email_subject = (
                    f"Order Placed & Payment Confirmed "
                    f"- Order #{order.id}"
                )


                email_body = f"""
Hello {user.name},

Your order has been placed successfully and your payment has been confirmed.

Order Details
------------------------------
Order ID: #{order.id}
Amount Paid: ₹{order.total_amount:.2f}
Payment Status: Paid
Order Status: Confirmed

Your order is now being processed.

Thank you for shopping with Smart E-Commerce!

Regards,

Smart E-Commerce Team
"""


                await send_email(

                    recipient=user.email,

                    subject=email_subject,

                    body=email_body
                )


                print(
                    "Order placed confirmation email sent successfully"
                )


            except Exception as email_exc:

                print(
                    "ORDER PLACED EMAIL ERROR:",
                    repr(email_exc)
                )


            # ==================================================
            # WEBHOOK SUCCESS
            # ==================================================

            print(
                "Webhook processing completed successfully"
            )


            return {
                "status": "success"
            }


        except Exception as exc:

            db.rollback()


            print(
                "\n===================================="
            )

            print(
                "WEBHOOK DATABASE ERROR"
            )

            print(
                "ERROR:",
                repr(exc)
            )

            print(
                "===================================="
            )


            raise HTTPException(
                status_code=500,
                detail="Webhook processing failed"
            )


    # ========================================================
    # PAYMENT INTENT SUCCEEDED
    # ========================================================

    elif event_type == "payment_intent.succeeded":

        payment_intent = event["data"]["object"]

        payment_intent_id = payment_intent["id"]


        print(
            "PaymentIntent succeeded:",
            payment_intent_id
        )


        print(
            "Webhook processing completed successfully"
        )


        return {
            "status": "success"
        }


    # ========================================================
    # PAYMENT INTENT CREATED
    # ========================================================

    elif event_type == "payment_intent.created":

        payment_intent = event["data"]["object"]


        print(
            "PaymentIntent created:",
            payment_intent["id"]
        )


        print(
            "Webhook processing completed successfully"
        )


        return {
            "status": "success"
        }


    # ========================================================
    # PAYMENT INTENT FAILED
    # ========================================================

    elif event_type == "payment_intent.payment_failed":

        payment_intent = event["data"]["object"]

        payment_intent_id = payment_intent["id"]


        print(
            "PaymentIntent failed:",
            payment_intent_id
        )


        try:

            payment = (
                db.query(Payment)
                .filter(
                    Payment.payment_intent_id
                    == payment_intent_id
                )
                .first()
            )


            if payment:

                payment.status = "failed"


                order = (
                    db.query(Order)
                    .filter(
                        Order.id == payment.order_id
                    )
                    .first()
                )


                if order:

                    order.payment_status = "failed"


                    user = (
                        db.query(User)
                        .filter(
                            User.id == order.user_id
                        )
                        .first()
                    )


                    if user:

                        notification = Notification(

                            user_id=user.id,

                            type="payment_failed",

                            message=(
                                f"Payment failed for "
                                f"Order #{order.id}"
                            ),

                            read_status="unread"
                        )


                        db.add(
                            notification
                        )


                db.commit()


            print(
                "Payment failure processed successfully"
            )


            return {
                "status": "success"
            }


        except Exception as exc:

            db.rollback()


            print(
                "PAYMENT FAILED WEBHOOK ERROR:",
                repr(exc)
            )


            raise HTTPException(
                status_code=500,
                detail="Payment failure processing failed"
            )


    # ========================================================
    # CHARGE SUCCEEDED
    # ========================================================

    elif event_type == "charge.succeeded":

        charge = event["data"]["object"]


        print(
            "Charge succeeded:",
            charge["id"]
        )


        print(
            "Webhook processing completed successfully"
        )


        return {
            "status": "success"
        }


    # ========================================================
    # CHARGE UPDATED
    # ========================================================

    elif event_type == "charge.updated":

        charge = event["data"]["object"]


        print(
            "Charge updated:",
            charge["id"]
        )


        print(
            "Webhook processing completed successfully"
        )


        return {
            "status": "success"
        }


    # ========================================================
    # UNHANDLED EVENT
    # ========================================================

    else:

        print(
            "Unhandled Stripe event:",
            event_type
        )


        print(
            "Webhook processing completed successfully"
        )


        return {
            "status": "success"
        }

