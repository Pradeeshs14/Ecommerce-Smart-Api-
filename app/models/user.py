from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    email = Column(
        String(150),
        unique=True,
        nullable=False
    )

    password = Column(String(255), nullable=False)

    role = Column(
        String(50),
        nullable=False,
        default="customer"
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # ============================================================
    # CART RELATIONSHIP
    # ============================================================

    cart_items = relationship(
        "Cart",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # ============================================================
    # ORDER RELATIONSHIP
    # ============================================================

    orders = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan"
    )

        # ============================================================
    # NOTIFICATION RELATIONSHIP
    # ============================================================

    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan"
    )