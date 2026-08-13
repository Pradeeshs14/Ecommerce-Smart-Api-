from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.cart import Cart
from app.models.product import Product
from app.schemas.cart import (
    CartCreate,
    CartUpdate,
    CartResponse
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/cart",
    tags=["Cart"]
)


# ============================================================
# ADD PRODUCT TO CART
# ============================================================

@router.post(
    "/",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED
)
def add_to_cart(
    cart_data: CartCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    product = (
        db.query(Product)
        .filter(Product.id == cart_data.product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    if product.stock < cart_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient stock"
        )

    existing_cart = (
        db.query(Cart)
        .filter(
            Cart.user_id == int(current_user),
            Cart.product_id == cart_data.product_id
        )
        .first()
    )

    if existing_cart:

        new_quantity = (
            existing_cart.quantity
            + cart_data.quantity
        )

        if product.stock < new_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient stock"
            )

        existing_cart.quantity = new_quantity

        db.commit()
        db.refresh(existing_cart)

        return existing_cart

    new_cart = Cart(
        user_id=int(current_user),
        product_id=cart_data.product_id,
        quantity=cart_data.quantity
    )

    db.add(new_cart)
    db.commit()
    db.refresh(new_cart)

    return new_cart

    # ============================================================
# GET CUSTOMER CART
# ============================================================

@router.get(
    "/",
    response_model=list[CartResponse]
)
def get_cart(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    cart_items = (
        db.query(Cart)
        .filter(
            Cart.user_id == int(current_user)
        )
        .all()
    )

    return cart_items

   # ============================================================
# UPDATE CART QUANTITY
# ============================================================

@router.put(
    "/{cart_id}",
    response_model=CartResponse
)
def update_cart(
    cart_id: int,
    cart_data: CartUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    cart_item = (
        db.query(Cart)
        .filter(
            Cart.id == cart_id,
            Cart.user_id == int(current_user)
        )
        .first()
    )

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )

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

    if product.stock < cart_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient stock"
        )

    cart_item.quantity = cart_data.quantity

    db.commit()
    db.refresh(cart_item)

    return cart_item

    # ============================================================
# DELETE CART ITEM
# ============================================================

@router.delete(
    "/{cart_id}"
)
def delete_cart_item(
    cart_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    cart_item = (
        db.query(Cart)
        .filter(
            Cart.id == cart_id,
            Cart.user_id == int(current_user)
        )
        .first()
    )

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )

    db.delete(cart_item)
    db.commit()

    return {
        "message": "Cart item removed successfully"
    }