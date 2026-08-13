from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from app.core.database import get_db
from app.core.security import (
    get_current_user,
    require_role
)
from app.models.cart import Cart
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.schemas.order import OrderResponse


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
    current_user=Depends(get_current_user)
):

    orders = (
        db.query(Order)
        .filter(
            Order.user_id == int(current_user)
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
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED
)
def checkout(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    user_id = int(current_user)

    # ============================================================
    # GET CUSTOMER CART
    # ============================================================

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

    # ============================================================
    # CHECK STOCK AND CALCULATE TOTAL
    # ============================================================

    total_amount = 0

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
                detail=f"Insufficient stock for {product.name}"
            )

        total_amount += (
            product.price * cart_item.quantity
        )

        products.append(
            (cart_item, product)
        )

    # ============================================================
    # CREATE ORDER
    # ============================================================

    new_order = Order(
        user_id=user_id,
        total_amount=total_amount,
        status="pending"
    )

    db.add(new_order)

    db.flush()

    # ============================================================
    # CREATE ORDER ITEMS
    # ============================================================

    for cart_item, product in products:

        order_item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            quantity=cart_item.quantity,
            price=product.price
        )

        db.add(order_item)

        product.stock -= cart_item.quantity

    # ============================================================
    # CLEAR CART
    # ============================================================

    for cart_item in cart_items:
        db.delete(cart_item)

    # ============================================================
    # SAVE ORDER
    # ============================================================

    db.commit()

    db.refresh(new_order)

    return new_order

    # ============================================================
# ADMIN - GET ALL ORDERS
# ============================================================

@router.get(
    "/admin/all",
    response_model=list[OrderResponse]
)
def get_all_orders(
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin"))
):

    orders = (
        db.query(Order)
        .order_by(
            Order.created_at.desc()
        )
        .all()
    )

    return orders