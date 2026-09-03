
from datetime import datetime, timedelta

import stripe  # type: ignore

from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from app.core.config import STRIPE_SECRET_KEY
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.email import send_email

from app.models.cart import Cart
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.return_request import ReturnRequest
from app.models.notification import Notification
from app.models.user import User

from app.services.websocket_manager import manager

from app.schemas.order import (
    CheckoutResponse,
    OrderResponse,
    OrderStatusUpdate,
)

from app.schemas.return_request import (
    ReturnRequestCreate,
    ReturnRequestResponse,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


# ============================================================
# STRIPE CONFIGURATION
# ============================================================

stripe.api_key = STRIPE_SECRET_KEY


# ============================================================
# CHECKOUT
# ============================================================

@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
def checkout(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    user_id = int(current_user)

    # --------------------------------------------------------
    # GET CART
    # --------------------------------------------------------

    cart_items = (
        db.query(Cart)
        .filter(Cart.user_id == user_id)
        .all()
    )

    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty",
        )

    # --------------------------------------------------------
    # VALIDATE CART + CALCULATE TOTAL
    # --------------------------------------------------------

    total_amount = 0.0
    products = []

    for cart_item in cart_items:

        product = (
            db.query(Product)
            .filter(Product.id == cart_item.product_id)
            .first()
        )

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {cart_item.product_id} not found",
            )

        if product.stock < cart_item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough stock for product {product.name}",
            )

        total_amount += product.price * cart_item.quantity

        products.append(
            (cart_item, product)
        )

    # Stripe uses smallest currency unit.
    # INR = paise

    amount_in_paise = int(
        round(total_amount * 100)
    )

    # --------------------------------------------------------
    # CREATE ORDER
    # --------------------------------------------------------

    new_order = Order(
        user_id=user_id,
        total_amount=total_amount,
        status="pending",
        payment_status="pending",
    )

    db.add(new_order)

    db.flush()

    # --------------------------------------------------------
    # CREATE ORDER ITEMS + REDUCE STOCK
    # --------------------------------------------------------

    for cart_item, product in products:

        order_item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            quantity=cart_item.quantity,
            price=product.price,
        )

        db.add(order_item)

        product.stock -= cart_item.quantity

    # --------------------------------------------------------
    # CREATE STRIPE CHECKOUT SESSION
    # --------------------------------------------------------

    try:

        checkout_session = stripe.checkout.Session.create(

            mode="payment",

            payment_method_types=[
                "card",
            ],

            line_items=[
                {
                    "price_data": {
                        "currency": "inr",

                        "product_data": {
                            "name": f"Order #{new_order.id}",
                        },

                        "unit_amount": amount_in_paise,
                    },

                    "quantity": 1,
                }
            ],

            metadata={
                "order_id": str(new_order.id),
                "user_id": str(user_id),
            },

            payment_intent_data={
                "metadata": {
                    "order_id": str(new_order.id),
                    "user_id": str(user_id),
                }
            },

            success_url=(
                "http://localhost:3000/"
                "payment/success"
                "?session_id={CHECKOUT_SESSION_ID}"
            ),

            cancel_url=(
                "http://localhost:3000/"
                "payment/cancel"
            ),
        )

    except stripe.StripeError as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(exc)}",
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Checkout error: {str(exc)}",
        )

    # --------------------------------------------------------
    # PAYMENT INTENT
    # --------------------------------------------------------

    # Stripe Checkout may not create the PaymentIntent
    # until the customer actually completes payment.

    payment_intent_id = checkout_session.payment_intent

    # --------------------------------------------------------
    # CREATE PAYMENT RECORD
    # --------------------------------------------------------

    payment = Payment(
        order_id=new_order.id,
        amount=total_amount,
        payment_method="card",
        transaction_id=payment_intent_id,
        status="pending",
        timestamp=datetime.utcnow(),
        payment_intent_id=payment_intent_id,
        checkout_session_id=checkout_session.id,
    )

    db.add(payment)

    # --------------------------------------------------------
    # CLEAR CART
    # --------------------------------------------------------

    for cart_item in cart_items:

        db.delete(cart_item)

    # --------------------------------------------------------
    # COMMIT DATABASE
    # --------------------------------------------------------

    try:

        db.commit()

        db.refresh(new_order)

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(exc)}",
        )

    # --------------------------------------------------------
    # RETURN CHECKOUT INFORMATION
    # --------------------------------------------------------

    return CheckoutResponse(
        order_id=new_order.id,
        total_amount=new_order.total_amount,
        payment_status=new_order.payment_status,
        payment_intent_id=payment_intent_id,
        checkout_session_id=checkout_session.id,
        checkout_url=checkout_session.url,
    )


# ============================================================
# GET CUSTOMER ORDERS
# ============================================================

@router.get(
    "/",
    response_model=list[OrderResponse],
)
def get_orders(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    user_id = int(current_user)

    orders = (
        db.query(Order)
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .all()
    )

    return orders


# ============================================================
# GET SINGLE ORDER
# ============================================================

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    user_id = int(current_user)

    order = (
        db.query(Order)
        .filter(
            Order.id == order_id,
            Order.user_id == user_id,
        )
        .first()
    )

    if not order:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return order


# ============================================================
# ADMIN - UPDATE ORDER STATUS
# ============================================================

@router.put(
    "/admin/{order_id}/status",
    response_model=OrderResponse,
)
async def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    user_id = int(current_user)

    # --------------------------------------------------------
    # CHECK ADMIN
    # --------------------------------------------------------

    admin_user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not admin_user:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if admin_user.role != "admin":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # --------------------------------------------------------
    # FIND ORDER
    # --------------------------------------------------------

    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .first()
    )

    if not order:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # --------------------------------------------------------
    # FIND CUSTOMER
    # --------------------------------------------------------

    customer = (
        db.query(User)
        .filter(User.id == order.user_id)
        .first()
    )

    if not customer:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    # --------------------------------------------------------
    # ALLOWED STATUS
    # --------------------------------------------------------

    allowed_statuses = {
        "pending",
        "confirmed",
        "shipped",
        "delivered",
        "cancelled",
        "return_requested",
        "returned",
        "refunded",
    }

    if status_data.status not in allowed_statuses:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid status. Allowed values: "
                f"{', '.join(sorted(allowed_statuses))}"
            ),
        )

    # --------------------------------------------------------
    # UPDATE STATUS
    # --------------------------------------------------------

    order.status = status_data.status

    # --------------------------------------------------------
    # DELIVERY DATE
    # --------------------------------------------------------

    if status_data.status == "delivered":

        order.delivered_at = datetime.utcnow()

    # --------------------------------------------------------
    # CREATE DELIVERY NOTIFICATION
    # --------------------------------------------------------

    if status_data.status == "delivered":

        delivery_notification = Notification(
            user_id=order.user_id,
            type="order_delivered",
            message=(
                f"Your Order #{order.id} "
                f"has been delivered successfully."
            ),
            read_status="unread",
        )

        db.add(delivery_notification)

    # --------------------------------------------------------
    # SAVE DATABASE
    # --------------------------------------------------------

    try:

        db.commit()

        db.refresh(order)

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(exc)}",
        )

    # --------------------------------------------------------
    # DELIVERY WEBSOCKET NOTIFICATION
    # --------------------------------------------------------

    if status_data.status == "delivered":

        try:

            await manager.send_to_user(
                order.user_id,
                {
                    "event": "order_delivered",
                    "order_id": order.id,
                    "status": "delivered",
                    "payment_status": order.payment_status,
                    "message": (
                        f"Your Order #{order.id} "
                        f"has been delivered successfully."
                    ),
                },
            )

            print(
                "Real-time delivery notification sent"
            )

        except Exception as websocket_exc:

            print(
                "WEBSOCKET DELIVERY ERROR:",
                repr(websocket_exc)
            )

        # ----------------------------------------------------
        # SEND DELIVERY EMAIL
        # ----------------------------------------------------

        try:

            delivered_subject = (
                f"Order Delivered - Order #{order.id}"
            )

            delivered_body = f"""
Hello {customer.name},

Your order has been delivered successfully.

Order Details
------------------------------
Order ID: #{order.id}
Order Status: Delivered
Payment Status: {order.payment_status}
Total Amount: ₹{order.total_amount:.2f}

Thank you for shopping with Smart E-Commerce!

We hope you enjoy your purchase.

Regards,

Smart E-Commerce Team
"""

            await send_email(
                recipient=customer.email,
                subject=delivered_subject,
                body=delivered_body,
            )

            print(
                "Order delivered email sent successfully"
            )

        except Exception as email_exc:

            print(
                "DELIVERY EMAIL ERROR:",
                repr(email_exc)
            )

    # --------------------------------------------------------
    # RETURN UPDATED ORDER
    # --------------------------------------------------------

    return order


# ============================================================
# CUSTOMER - CREATE RETURN REQUEST
# ============================================================

@router.post(
    "/{order_id}/return",
    response_model=ReturnRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_return_request(
    order_id: int,
    data: ReturnRequestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    user_id = int(current_user)

    # --------------------------------------------------------
    # FIND ORDER
    # --------------------------------------------------------

    order = (
        db.query(Order)
        .filter(
            Order.id == order_id,
            Order.user_id == user_id,
        )
        .first()
    )

    if not order:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # --------------------------------------------------------
    # ORDER MUST BE DELIVERED
    # --------------------------------------------------------

    if order.status != "delivered":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only delivered orders can be returned",
        )

    # --------------------------------------------------------
    # CHECK DELIVERY DATE
    # --------------------------------------------------------

    if not order.delivered_at:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivery date not available",
        )

    # --------------------------------------------------------
    # CHECK 7-DAY RETURN WINDOW
    # --------------------------------------------------------

    if datetime.utcnow() > (
        order.delivered_at + timedelta(days=7)
    ):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return period has expired",
        )

    # --------------------------------------------------------
    # CHECK EXISTING RETURN
    # --------------------------------------------------------

    existing_return = (
        db.query(ReturnRequest)
        .filter(
            ReturnRequest.order_id == order_id,
            ReturnRequest.status.in_(
                [
                    "pending",
                    "approved",
                    "returned",
                    "refunded",
                ]
            ),
        )
        .first()
    )

    if existing_return:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return request already exists",
        )

    # --------------------------------------------------------
    # CREATE RETURN REQUEST
    # --------------------------------------------------------

    return_request = ReturnRequest(
        order_id=order.id,
        user_id=user_id,
        reason=data.reason,
        comment=data.comment,
        status="pending",
        created_at=datetime.utcnow(),
    )

    db.add(return_request)

    # --------------------------------------------------------
    # UPDATE ORDER STATUS
    # --------------------------------------------------------

    order.status = "return_requested"

    db.commit()

    db.refresh(return_request)

    return return_request


# ============================================================
# ADMIN - GET ALL RETURN REQUESTS
# ============================================================

@router.get(
    "/admin/returns",
    response_model=list[ReturnRequestResponse],
)
def get_all_returns(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    user_id = int(current_user)

    # --------------------------------------------------------
    # CHECK ADMIN
    # --------------------------------------------------------

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.role != "admin":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # --------------------------------------------------------
    # GET ALL RETURN REQUESTS
    # --------------------------------------------------------

    return_requests = (
        db.query(ReturnRequest)
        .order_by(ReturnRequest.created_at.desc())
        .all()
    )

    return return_requests


# ============================================================
# ADMIN - APPROVE RETURN + REFUND
# ============================================================

@router.put(
    "/admin/returns/{return_id}/approve",
    response_model=ReturnRequestResponse,
)
async def approve_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    user_id = int(current_user)

    # --------------------------------------------------------
    # CHECK ADMIN
    # --------------------------------------------------------

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.role != "admin":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # --------------------------------------------------------
    # FIND RETURN REQUEST
    # --------------------------------------------------------

    return_request = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.id == return_id)
        .first()
    )

    if not return_request:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    if return_request.status != "pending":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return request is not pending",
        )

    # --------------------------------------------------------
    # FIND ORDER
    # --------------------------------------------------------

    order = (
        db.query(Order)
        .filter(Order.id == return_request.order_id)
        .first()
    )

    if not order:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # --------------------------------------------------------
    # FIND PAYMENT
    # --------------------------------------------------------

    payment = (
        db.query(Payment)
        .filter(Payment.order_id == order.id)
        .first()
    )

    if not payment:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found",
        )

    # --------------------------------------------------------
    # PAYMENT INTENT REQUIRED
    # --------------------------------------------------------

    if not payment.payment_intent_id:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PaymentIntent ID not found",
        )

    # --------------------------------------------------------
    # PAYMENT MUST BE PAID
    # --------------------------------------------------------

    if payment.status not in {
        "paid",
        "succeeded",
    }:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment has not been completed",
        )

    # --------------------------------------------------------
    # RETURN APPROVED
    # --------------------------------------------------------

    return_request.status = "approved"

    # --------------------------------------------------------
    # ORDER RETURNED
    # --------------------------------------------------------

    order.status = "returned"

    # --------------------------------------------------------
    # APPROVED NOTIFICATION
    # --------------------------------------------------------

    approved_notification = Notification(
        user_id=return_request.user_id,
        type="return_approved",
        message=(
            f"Your return request for order "
            f"#{return_request.order_id} has been approved."
        ),
        read_status="unread",
    )

    db.add(approved_notification)

    # --------------------------------------------------------
    # RESTORE STOCK
    # --------------------------------------------------------

    order_items = (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order.id)
        .all()
    )

    for order_item in order_items:

        product = (
            db.query(Product)
            .filter(Product.id == order_item.product_id)
            .first()
        )

        if product:

            product.stock += order_item.quantity

    # --------------------------------------------------------
    # CREATE STRIPE REFUND
    # --------------------------------------------------------

    try:

        refund = stripe.Refund.create(
            payment_intent=payment.payment_intent_id,
            metadata={
                "order_id": str(order.id),
                "return_request_id": str(return_request.id),
                "user_id": str(order.user_id),
            },
        )

    except stripe.StripeError as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe refund failed: {str(exc)}",
        )

    # --------------------------------------------------------
    # REFUND COMPLETED
    # --------------------------------------------------------

    return_request.status = "refunded"

    order.status = "refunded"

    order.payment_status = "refunded"

    payment.status = "refunded"

    payment.refund_id = refund.id

    # --------------------------------------------------------
    # REFUND COMPLETED NOTIFICATION
    # --------------------------------------------------------

    refund_notification = Notification(
        user_id=return_request.user_id,
        type="refund_completed",
        message=(
            f"Your refund for order "
            f"#{return_request.order_id} has been completed."
        ),
        read_status="unread",
    )

    db.add(refund_notification)

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    try:

        db.commit()

        db.refresh(return_request)

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(exc)}",
        )

    return return_request


# ============================================================
# ADMIN - REJECT RETURN
# ============================================================

@router.put(
    "/admin/returns/{return_id}/reject",
    response_model=ReturnRequestResponse,
)
async def reject_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    user_id = int(current_user)

    # --------------------------------------------------------
    # CHECK ADMIN
    # --------------------------------------------------------

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.role != "admin":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # --------------------------------------------------------
    # FIND RETURN REQUEST
    # --------------------------------------------------------

    return_request = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.id == return_id)
        .first()
    )

    if not return_request:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    if return_request.status != "pending":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return request is not pending",
        )

    # --------------------------------------------------------
    # UPDATE RETURN
    # --------------------------------------------------------

    return_request.status = "rejected"

    # --------------------------------------------------------
    # UPDATE ORDER
    # --------------------------------------------------------

    order = (
        db.query(Order)
        .filter(Order.id == return_request.order_id)
        .first()
    )

    if order:

        order.status = "delivered"

    # --------------------------------------------------------
    # CREATE NOTIFICATION
    # --------------------------------------------------------

    notification = Notification(
        user_id=return_request.user_id,
        type="return_rejected",
        message=(
            f"Your return request for order "
            f"#{return_request.order_id} has been rejected."
        ),
        read_status="unread",
    )

    db.add(notification)

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    try:

        db.commit()

        db.refresh(return_request)

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(exc)}",
        )

    # --------------------------------------------------------
    # SEND RETURN REJECTION EMAIL
    # --------------------------------------------------------

    if order:

        try:

            rejected_subject = (
                f"Return Rejected - Order #{return_request.order_id}"
            )

            rejected_body = f"""
Hello {user.name},

We are sorry to inform you that your return request has been rejected.

Order Details
------------------------------
Order ID: #{return_request.order_id}
Return Request ID: #{return_request.id}
Return Status: Rejected
Reason: {return_request.reason}

If you have any questions, please contact our support team.

Thank you,

Smart E-Commerce Team
"""

            # Get actual customer
            customer = (
                db.query(User)
                .filter(User.id == order.user_id)
                .first()
            )

            if customer:

                await send_email(
                    recipient=customer.email,
                    subject=rejected_subject,
                    body=rejected_body,
                )

                print(
                    "Return rejection email sent successfully"
                )

        except Exception as email_exc:

            print(
                "RETURN REJECTION EMAIL ERROR:",
                repr(email_exc)
            )

    return return_request

