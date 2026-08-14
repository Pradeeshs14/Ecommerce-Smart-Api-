from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from app.core.database import get_db
from app.core.security import require_role
from app.models.product import Product
from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductUpdate
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/products",
    tags=["Products"]
)


# ============================================================
# CREATE PRODUCT
# ============================================================

@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED
)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin"))
):

    new_product = Product(
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        stock=product_data.stock,
        images=product_data.images,
        category=product_data.category,
        popularity=product_data.popularity
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return new_product


# ============================================================
# GET ALL PRODUCTS + FILTERS
# ============================================================

@router.get(
    "/",
    response_model=list[ProductResponse]
)
def get_products(
    category: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    popularity: int | None = None,
    in_stock: bool | None = None,
    db: Session = Depends(get_db)
):

    query = db.query(Product)

    # Category filter
    if category:
        query = query.filter(
            Product.category == category
        )

    # Minimum price filter
    if price_min is not None:
        query = query.filter(
            Product.price >= price_min
        )

    # Maximum price filter
    if price_max is not None:
        query = query.filter(
            Product.price <= price_max
        )

    # Popularity filter
    if popularity is not None:
        query = query.filter(
            Product.popularity >= popularity
        )

    # Stock availability filter
    if in_stock is True:
        query = query.filter(
            Product.stock > 0
        )

    if in_stock is False:
        query = query.filter(
            Product.stock == 0
        )

    return query.all()


# ============================================================
# GET PRODUCTS BY CATEGORY
# ============================================================

@router.get(
    "/category/{category}",
    response_model=list[ProductResponse]
)
def get_products_by_category(
    category: str,
    db: Session = Depends(get_db)
):

    products = (
        db.query(Product)
        .filter(Product.category == category)
        .all()
    )

    return products


# ============================================================
# GET PRODUCT BY ID
# ============================================================

@router.get(
    "/{product_id}",
    response_model=ProductResponse
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if not product:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return product


# ============================================================
# UPDATE PRODUCT
# ============================================================

@router.put(
    "/{product_id}",
    response_model=ProductResponse
)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin"))
):

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if not product:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    update_data = product_data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():

        setattr(
            product,
            field,
            value
        )

    db.commit()
    db.refresh(product)

    return product


# ============================================================
# DELETE PRODUCT
# ============================================================

@router.delete(
    "/{product_id}",
    status_code=status.HTTP_200_OK
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin"))
):

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if not product:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    db.delete(product)
    db.commit()

    return {
        "message": "Product deleted successfully"
    }