from sqlalchemy import Column, Float, Integer, String, Text  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore

from app.core.database import Base


# ============================================================
# PRODUCT MODEL
# ============================================================

class Product(Base):

    __tablename__ = "products"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(150),
        nullable=False
    )

    description = Column(
        Text,
        nullable=True
    )

    price = Column(
        Float,
        nullable=False
    )

    stock = Column(
        Integer,
        nullable=False,
        default=0
    )

    images = Column(
        String(500),
        nullable=True
    )

    cart_items = relationship(
        "Cart",
        back_populates="product",
        cascade="all, delete-orphan"
    )