from pydantic import BaseModel, Field # type: ignore


# ============================================================
# CART CREATE
# ============================================================

class CartCreate(BaseModel):

    product_id: int = Field(
        gt=0
    )

    quantity: int = Field(
        gt=0
    )


# ============================================================
# CART UPDATE
# ============================================================

class CartUpdate(BaseModel):

    quantity: int = Field(
        gt=0
    )


# ============================================================
# CART PRODUCT RESPONSE
# ============================================================

class CartProductResponse(BaseModel):

    id: int
    name: str
    price: float
    images: str | None = None


# ============================================================
# CART RESPONSE
# ============================================================

class CartResponse(BaseModel):

    id: int
    product_id: int
    quantity: int
    product: CartProductResponse