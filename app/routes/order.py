from datetime import datetime

from fastapi import ( # type: ignore
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session  # type: ignore

import stripe  # type: ignore

from app.core.config import STRIPE_SECRET_KEY
from app.core.database import get_db
from app.core.security import (
    get_current_user,
    require_role,
)
from app.core.email import send_email

from app.models.cart import Cart
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.notification import Notification
from app.models.user import User

from app.schemas.order import (
    CheckoutResponse,
    OrderResponse,
    OrderStatusUpdate,
)

from app.services.websocket_manager import manager


# ============================================================
# STRIPE CONFIGURATION
# ============================================================

stripe.api_key = STRIPE_SECRET_KEY

print(
    "STRIPE KEY PREFIX:",
    STRIPE_SECRET_KEY[:8]
)

print(
    "STRIPE KEY LENGTH:",
    len(STRIPE_SECRET_KEY)
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)


# ============================================================
# GET CUSTOMER ORDERS
# ============================================================

@router.get(
    "/",
    response_model=list[OrderResponse]
)
def get_customer_orders(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    user_id = int(current_user)

    orders = (
        db.query(Order)
        .filter(
            Order.user_id == user_id
        )
        .order_by(
            Order.created_at.desc()
        )
        .all()
    )

    return orders


# ============================================================
# CHECKOUT
# ============================================================

@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED
)
def checkout(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    user_id = int(current_user)

    # ========================================================
    # CHECK STRIPE CONFIGURATION
    # ========================================================

    if not STRIPE_SECRET_KEY:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe is not configured"
        )

    # ========================================================
    # GET CUSTOMER CART
    # ========================================================

    cart_items = (
        db.query(Cart)
        .filter(
            Cart.user_id == user_id
        )
        .all()
    )

    if not cart_items:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty"
        )

    # ========================================================
    # CHECK STOCK AND CALCULATE TOTAL
    # ========================================================

    total_amount = 0.0
    products = []

    for cart_item in cart_items:

        product = (
            db.query(Product)
            .filter(
                Product.id == cart_item.product_id
            )
            .first()
        )

        if not product:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        if product.stock < cart_item.quantity:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient stock for "
                    f"{product.name}"
                )
            )

        total_amount += (
            product.price *
            cart_item.quantity
        )

        products.append(
            (cart_item, product)
        )

    # ========================================================
    # CONVERT TO SMALLEST CURRENCY UNIT
    # ========================================================

    amount_in_cents = int(
        round(total_amount * 100)
    )

    # ========================================================
    # CREATE ORDER
    # ========================================================

    new_order = Order(
        user_id=user_id,
        total_amount=total_amount,
        status="pending",
        payment_status="pending"
    )

    db.add(new_order)

    db.flush()

    # ========================================================
    # CREATE ORDER ITEMS
    # ========================================================

    for cart_item, product in products:

        order_item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            quantity=cart_item.quantity,
            price=product.price
        )

        db.add(order_item)

        # Reduce stock
        product.stock -= cart_item.quantity

    # ========================================================
    # CREATE STRIPE PAYMENT
    # ========================================================

    try:

        # ----------------------------------------------------
        # PAYMENT INTENT
        # ----------------------------------------------------

        payment_intent = stripe.PaymentIntent.create(

            amount=amount_in_cents,

            currency="inr",

            metadata={
                "order_id": str(new_order.id),
                "user_id": str(user_id)
            }
        )

        # ----------------------------------------------------
        # CHECKOUT SESSION
        # ----------------------------------------------------

        checkout_session = stripe.checkout.Session.create(

            mode="payment",

            payment_method_types=[
                "card"
            ],

            line_items=[
                {
                    "price_data": {

                        "currency": "inr",

                        "product_data": {
                            "name": (
                                f"Order #{new_order.id}"
                            )
                        },

                        "unit_amount":
                            amount_in_cents
                    },

                    "quantity": 1
                }
            ],

            metadata={
                "order_id": str(new_order.id),
                "user_id": str(user_id)
            },

            success_url=(
                "http://localhost:3000/"
                "payment/success"
                "?session_id="
                "{CHECKOUT_SESSION_ID}"
            ),

            cancel_url=(
                "http://localhost:3000/"
                "payment/cancel"
            )
        )

    except stripe.StripeError as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Stripe payment creation failed: "
                f"{str(exc)}"
            )
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Payment setup failed: "
                f"{str(exc)}"
            )
        )

    # ========================================================
    # CREATE PAYMENT RECORD
    # ========================================================

    payment = Payment(
        order_id=new_order.id,
        amount=total_amount,
        payment_method="card",
        transaction_id=payment_intent.id,
        status="pending",
        timestamp=datetime.utcnow(),
        payment_intent_id=payment_intent.id,
        checkout_session_id=checkout_session.id
    )

    db.add(payment)

    # ========================================================
    # CLEAR CART
    # ========================================================

    for cart_item in cart_items:

        db.delete(cart_item)

    # ========================================================
    # SAVE DATABASE CHANGES
    # ========================================================

    try:

        db.commit()

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Order creation failed: "
                f"{str(exc)}"
            )
        )

    db.refresh(new_order)

    # ========================================================
    # RETURN CHECKOUT DETAILS
    # ========================================================

    return CheckoutResponse(

        order_id=new_order.id,

        total_amount=new_order.total_amount,

        payment_status=new_order.payment_status,

        payment_intent_id=payment_intent.id,

        checkout_session_id=checkout_session.id,

        checkout_url=checkout_session.url
    )


# ============================================================
# ADMIN - GET ALL ORDERS
# ============================================================

@router.get(
    "/admin/all",
    response_model=list[OrderResponse]
)
def get_all_orders(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_role("admin")
    ),
):

    orders = (
        db.query(Order)
        .order_by(
            Order.created_at.desc()
        )
        .all()
    )

    return orders


# ============================================================
# ADMIN - UPDATE ORDER STATUS
# ============================================================

@router.put(
    "/admin/{order_id}/status",
    response_model=OrderResponse
)
async def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_role("admin")
    ),
):

    # ========================================================
    # VALID STATUSES
    # ========================================================

    allowed_statuses = {
        "pending",
        "confirmed",
        "shipped",
        "delivered",
        "cancelled",
    }

    new_status = (
        status_data.status
        .lower()
        .strip()
    )

    if new_status not in allowed_statuses:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid order status. "
                "Allowed values: "
                "pending, confirmed, shipped, "
                "delivered, cancelled"
            )
        )

    # ========================================================
    # FIND ORDER
    # ========================================================

    order = (
        db.query(Order)
        .filter(
            Order.id == order_id
        )
        .first()
    )

    if not order:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # ========================================================
    # CHECK SAME STATUS
    # ========================================================

    if order.status == new_status:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Order is already "
                f"{new_status}"
            )
        )

    # ========================================================
    # SAVE OLD STATUS
    # ========================================================

    old_status = order.status

    # ========================================================
    # UPDATE ORDER STATUS
    # ========================================================

    order.status = new_status

    # ========================================================
    # CREATE NOTIFICATION
    # ========================================================

    notification = Notification(

        user_id=order.user_id,

        type="order_status_updated",

        message=(
            f"Your Order #{order.id} "
            f"status has been updated "
            f"to {new_status}"
        ),

        read_status="unread"
    )

    db.add(notification)

    # ========================================================
    # COMMIT DATABASE
    # ========================================================

    try:

        db.commit()

        db.refresh(order)

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Failed to update order status: "
                f"{str(exc)}"
            )
        )

    # ========================================================
    # WEBSOCKET NOTIFICATION
    # ========================================================

    try:

        await manager.send_to_user(

            order.user_id,

            {
                "event":
                    "order_status_updated",

                "order_id":
                    order.id,

                "old_status":
                    old_status,

                "status":
                    new_status,

                "payment_status":
                    order.payment_status,

                "message":
                    (
                        f"Your Order #{order.id} "
                        f"has been updated to "
                        f"{new_status}"
                    )
            }
        )

        print(
            "Real-time order status "
            "notification sent"
        )

    except Exception as websocket_exc:

        print(
            "WEBSOCKET ORDER STATUS ERROR:",
            repr(websocket_exc)
        )

    # ========================================================
    # SEND EMAIL
    # ========================================================

    try:

        user = (
            db.query(User)
            .filter(
                User.id == order.user_id
            )
            .first()
        )

        if user:

            email_subject = (
                f"Order #{order.id} "
                f"Status Updated - "
                f"Smart E-Commerce"
            )

            email_body = f"""
Hello {user.name},

Your order status has been updated.

Order Details
------------------------------

Order ID: #{order.id}

Previous Status: {old_status}

Current Status: {new_status}

Payment Status: {order.payment_status}

Thank you for shopping with
Smart E-Commerce.

Regards,

Smart E-Commerce Team
"""

            await send_email(
                recipient=user.email,
                subject=email_subject,
                body=email_body
            )

            print(
                "Order status email sent successfully"
            )

    except Exception as email_exc:

        print(
            "ORDER STATUS EMAIL ERROR:",
            repr(email_exc)
        )

        # Email failure should not
        # fail the order update.

    # ========================================================
    # RETURN UPDATED ORDER
    # ========================================================

    return order