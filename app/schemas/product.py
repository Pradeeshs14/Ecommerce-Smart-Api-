from pydantic import BaseModel, ConfigDict, Field # type: ignore


# ============================================================
# PRODUCT BASE
# ============================================================

class ProductBase(BaseModel):

    name: str = Field(
        min_length=1,
        max_length=150
    )

    description: str | None = None

    price: float = Field(
        gt=0
    )

    stock: int = Field(
        ge=0
    )

    images: str | None = None
    category: str | None = None

    popularity: int = Field(
    default=0,
    ge=0
)


# ============================================================
# PRODUCT CREATE
# ============================================================

class ProductCreate(ProductBase):
    pass


# ============================================================
# PRODUCT UPDATE
# ============================================================

class ProductUpdate(BaseModel):

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150
    )

    description: str | None = None

    price: float | None = Field(
        default=None,
        gt=0
    )

    stock: int | None = Field(
        default=None,
        ge=0
    )

    images: str | None = None

    category: str | None = None

    popularity: int | None = Field(
    default=None,
    ge=0
)


# ============================================================
# PRODUCT RESPONSE
# ============================================================

class ProductResponse(ProductBase):

    id: int

    model_config = ConfigDict(
        from_attributes=True
    )