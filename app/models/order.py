from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore

from app.core.database import Base


# ============================================================
# ORDER MODEL
# ============================================================

class Order(Base):

    __tablename__ = "orders"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    total_amount = Column(
        Float,
        nullable=False
    )

    status = Column(
        String(50),
        nullable=False,
        default="pending"
    )

    payment_status = Column(
        String(50),
        nullable=False,
        default="pending"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # ========================================================
    # USER RELATIONSHIP
    # ========================================================

    user = relationship(
        "User",
        back_populates="orders"
    )

    # ========================================================
    # ORDER ITEMS RELATIONSHIP
    # ========================================================

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )

    # ========================================================
    # PAYMENT RELATIONSHIP
    # ========================================================

    payment = relationship(
        "Payment",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan"
    )