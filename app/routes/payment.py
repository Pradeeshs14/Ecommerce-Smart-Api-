
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

            payment.status = "paid"


            # ==================================================
            # UPDATE ORDER
            # ==================================================

            order.payment_status = "paid"

            order.status = "confirmed"


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
                        "event": "order_status_updated",

                        "order_id": order.id,

                        "status": "confirmed",

                        "payment_status": "paid",

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
            # SEND CONFIRMATION EMAIL
            # ==================================================

            try:

                email_subject = (
                    f"Order #{order.id} Confirmed - "
                    f"Smart E-Commerce"
                )


                email_body = f"""
Hello {user.name},

Your payment has been successfully received.

Order Details
------------------------------

Order ID: #{order.id}

Amount Paid: ₹{order.total_amount:.2f}

Payment Status: Paid

Order Status: Confirmed

Thank you for shopping with Smart E-Commerce.

Your order is now confirmed and will be processed shortly.

Regards,

Smart E-Commerce Team
"""


                await send_email(

                    recipient=user.email,

                    subject=email_subject,

                    body=email_body
                )


                print(
                    "Confirmation email sent successfully"
                )


            except Exception as email_exc:

                print(
                    "EMAIL ERROR:",
                    repr(email_exc)
                )


            print(
                "Payment processing completed successfully"
            )


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
                detail=(
                    f"Webhook database error: "
                    f"{str(exc)}"
                )
            )


    # ========================================================
    # PAYMENT INTENT SUCCEEDED
    # ========================================================

    elif event_type == "payment_intent.succeeded":

        print(
            "PaymentIntent succeeded"
        )


    # ========================================================
    # PAYMENT INTENT CREATED
    # ========================================================

    elif event_type == "payment_intent.created":

        print(
            "PaymentIntent created"
        )


    # ========================================================
    # PAYMENT INTENT FAILED
    # ========================================================

    elif event_type == "payment_intent.payment_failed":

        payment_intent = event["data"]["object"]

        payment_intent_id = payment_intent["id"]

        print("\n====================================")
        print("PAYMENT INTENT PAYMENT FAILED")

        print(
            "PaymentIntent ID:",
            payment_intent_id
        )

        print("====================================")


        try:

            # ==================================================
            # FIND PAYMENT
            # ==================================================

            payment = (
                db.query(Payment)
                .filter(
                    Payment.payment_intent_id
                    == payment_intent_id
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


            # ==================================================
            # IDEMPOTENCY CHECK
            # ==================================================

            if payment.status == "failed":

                print(
                    "Payment already marked as FAILED"
                )

                return {
                    "status": "success",
                    "message": "Payment failure already processed"
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
            # GET FAILURE MESSAGE
            # ==================================================

            last_payment_error = (
                payment_intent.get(
                    "last_payment_error"
                )
            )


            failure_message = (
                "Payment failed"
            )


            if last_payment_error:

                failure_message = (
                    last_payment_error.get(
                        "message",
                        "Payment failed"
                    )
                )


            # ==================================================
            # UPDATE PAYMENT
            # ==================================================

            payment.status = "failed"


            # ==================================================
            # UPDATE ORDER
            # ==================================================

            order.payment_status = "failed"

            order.status = "payment_failed"


            # ==================================================
            # CREATE PAYMENT FAILURE NOTIFICATION
            # ==================================================

            notification = Notification(

                user_id=user.id,

                type="payment_failed",

                message=(
                    f"Payment failed for "
                    f"Order #{order.id}. "
                    f"{failure_message}"
                ),

                read_status="unread"
            )

            db.add(notification)


            # ==================================================
            # COMMIT DATABASE CHANGES
            # ==================================================

            db.commit()


            print(
                "Payment status updated to FAILED"
            )

            print(
                "Order payment status updated to FAILED"
            )

            print(
                "Order status updated to PAYMENT_FAILED"
            )

            print(
                "Payment failure notification created"
            )


            # ==================================================
            # REAL-TIME PAYMENT FAILURE
            # ==================================================

            try:

                await manager.send_to_user(

                    user.id,

                    {
                        "event": "payment_failed",

                        "order_id": order.id,

                        "payment_id": payment.id,

                        "payment_status": "failed",

                        "message": (
                            f"Payment failed for "
                            f"Order #{order.id}"
                        )
                    }
                )


                print(
                    "Real-time payment failure notification sent"
                )


            except Exception as websocket_exc:

                print(
                    "WEBSOCKET PAYMENT FAILURE ERROR:",
                    repr(websocket_exc)
                )


            # ==================================================
            # REAL-TIME ORDER UPDATE
            # ==================================================

            try:

                await manager.send_to_user(

                    user.id,

                    {
                        "event": "order_status_updated",

                        "order_id": order.id,

                        "status": "payment_failed",

                        "payment_status": "failed",

                        "message": (
                            f"Payment failed for "
                            f"Order #{order.id}"
                        )
                    }
                )


                print(
                    "Real-time failed order notification sent"
                )


            except Exception as websocket_exc:

                print(
                    "WEBSOCKET ORDER FAILURE ERROR:",
                    repr(websocket_exc)
                )


            # ==================================================
            # SEND PAYMENT FAILURE EMAIL
            # ==================================================

            try:

                email_subject = (
                    f"Payment Failed - "
                    f"Order #{order.id}"
                )


                email_body = f"""
Hello {user.name},

Unfortunately, your payment could not be completed.

Order Details
------------------------------

Order ID: #{order.id}

Amount: ₹{order.total_amount:.2f}

Payment Status: Failed

Order Status: Payment Failed

Reason:
{failure_message}

Please try the payment again.

If the amount was deducted from your account,
please contact our support team.

Regards,

Smart E-Commerce Team
"""


                await send_email(

                    recipient=user.email,

                    subject=email_subject,

                    body=email_body
                )


                print(
                    "Payment failure email sent successfully"
                )


            except Exception as email_exc:

                print(
                    "PAYMENT FAILURE EMAIL ERROR:",
                    repr(email_exc)
                )


            print(
                "Payment failure processing completed successfully"
            )


        except Exception as exc:

            db.rollback()

            print(
                "\n===================================="
            )

            print(
                "PAYMENT FAILURE DATABASE ERROR"
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
                detail=(
                    f"Payment failure processing error: "
                    f"{str(exc)}"
                )
            )


    # ========================================================
    # CHARGE SUCCEEDED
    # ========================================================

    elif event_type == "charge.succeeded":

        print(
            "Charge succeeded"
        )


    # ========================================================
    # CHARGE UPDATED
    # ========================================================

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

