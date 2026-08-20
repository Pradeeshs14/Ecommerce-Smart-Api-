from datetime import datetime

from pydantic import BaseModel  # type: ignore


# ============================================================
# ORDER ITEM RESPONSE
# ============================================================

class OrderItemResponse(BaseModel):

    id: int
    product_id: int
    quantity: int
    price: float


# ============================================================
# ORDER RESPONSE
# ============================================================

class OrderResponse(BaseModel):

    id: int
    user_id: int
    total_amount: float
    status: str
    payment_status: str
    created_at: datetime
    items: list[OrderItemResponse]


# ============================================================
# CHECKOUT RESPONSE
# ============================================================

class CheckoutResponse(BaseModel):

    order_id: int
    total_amount: float
    payment_status: str
    payment_intent_id: str
    checkout_session_id: str
    checkout_url: str