from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.websocket_manager import manager

from app.models.cart import Cart
from app.models.product import Product

from app.schemas.cart import (
    CartCreate,
    CartUpdate,
    CartResponse,
    CartTotalResponse
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
async def add_to_cart(
    cart_data: CartCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    user_id = int(current_user)

    # ========================================================
    # FIND PRODUCT
    # ========================================================

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

    # ========================================================
    # CHECK STOCK
    # ========================================================

    if product.stock < cart_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient stock"
        )

    # ========================================================
    # CHECK EXISTING CART ITEM
    # ========================================================

    existing_cart = (
        db.query(Cart)
        .filter(
            Cart.user_id == user_id,
            Cart.product_id == cart_data.product_id
        )
        .first()
    )

    # ========================================================
    # UPDATE EXISTING CART ITEM
    # ========================================================

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

        existing_cart.item_total = (
            product.price * existing_cart.quantity
        )

        # ====================================================
        # WEBSOCKET - CART UPDATED
        # ====================================================

        await manager.send_to_user(
            user_id,
            {
                "event": "cart_updated",
                "action": "quantity_updated",
                "message": "Your cart has been updated",
                "cart_id": existing_cart.id,
                "product_id": existing_cart.product_id,
                "quantity": existing_cart.quantity
            }
        )

        return existing_cart

    # ========================================================
    # CREATE NEW CART ITEM
    # ========================================================

    new_cart = Cart(
        user_id=user_id,
        product_id=cart_data.product_id,
        quantity=cart_data.quantity
    )

    db.add(new_cart)
    db.commit()
    db.refresh(new_cart)

    new_cart.item_total = (
        product.price * new_cart.quantity
    )

    # ========================================================
    # WEBSOCKET - CART UPDATED
    # ========================================================

    await manager.send_to_user(
        user_id,
        {
            "event": "cart_updated",
            "action": "item_added",
            "message": "Product added to your cart",
            "cart_id": new_cart.id,
            "product_id": new_cart.product_id,
            "quantity": new_cart.quantity
        }
    )

    return new_cart


# ============================================================
# GET CUSTOMER CART
# ============================================================

@router.get(
    "/",
    response_model=CartTotalResponse
)
def get_cart(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    user_id = int(current_user)

    cart_items = (
        db.query(Cart)
        .filter(
            Cart.user_id == user_id
        )
        .all()
    )

    cart_total = 0.0

    for item in cart_items:

        item.item_total = (
            item.product.price * item.quantity
        )

        cart_total += item.item_total

    return {
        "items": cart_items,
        "cart_total": cart_total
    }


# ============================================================
# UPDATE CART QUANTITY
# ============================================================

@router.put(
    "/{cart_id}",
    response_model=CartResponse
)
async def update_cart(
    cart_id: int,
    cart_data: CartUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    user_id = int(current_user)

    # ========================================================
    # FIND CART ITEM
    # ========================================================

    cart_item = (
        db.query(Cart)
        .filter(
            Cart.id == cart_id,
            Cart.user_id == user_id
        )
        .first()
    )

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )

    # ========================================================
    # FIND PRODUCT
    # ========================================================

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

    # ========================================================
    # CHECK STOCK
    # ========================================================

    if product.stock < cart_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient stock"
        )

    # ========================================================
    # UPDATE QUANTITY
    # ========================================================

    cart_item.quantity = cart_data.quantity

    db.commit()
    db.refresh(cart_item)

    cart_item.item_total = (
        product.price * cart_item.quantity
    )

    # ========================================================
    # WEBSOCKET - CART UPDATED
    # ========================================================

    await manager.send_to_user(
        user_id,
        {
            "event": "cart_updated",
            "action": "quantity_updated",
            "message": "Your cart quantity has been updated",
            "cart_id": cart_item.id,
            "product_id": cart_item.product_id,
            "quantity": cart_item.quantity
        }
    )

    return cart_item


# ============================================================
# DELETE CART ITEM
# ============================================================

@router.delete(
    "/{cart_id}"
)
async def delete_cart_item(
    cart_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    user_id = int(current_user)

    # ========================================================
    # FIND CART ITEM
    # ========================================================

    cart_item = (
        db.query(Cart)
        .filter(
            Cart.id == cart_id,
            Cart.user_id == user_id
        )
        .first()
    )

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )

    # ========================================================
    # SAVE CART ID BEFORE DELETE
    # ========================================================

    deleted_cart_id = cart_item.id

    # ========================================================
    # DELETE CART ITEM
    # ========================================================

    db.delete(cart_item)
    db.commit()

    # ========================================================
    # WEBSOCKET - CART UPDATED
    # ========================================================

    await manager.send_to_user(
        user_id,
        {
            "event": "cart_updated",
            "action": "item_deleted",
            "message": "An item was removed from your cart",
            "cart_id": deleted_cart_id
        }
    )

    return {
        "message": "Cart item removed successfully"
    }