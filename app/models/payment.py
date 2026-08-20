from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore

from app.core.database import Base


# ============================================================
# PAYMENT MODEL
# ============================================================

class Payment(Base):

    __tablename__ = "payments"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # ========================================================
    # ORDER REFERENCE
    # ========================================================

    order_id = Column(
        Integer,
        ForeignKey("orders.id"),
        nullable=False,
        unique=True
    )

    # ========================================================
    # PAYMENT AMOUNT
    # ========================================================

    amount = Column(
        Float,
        nullable=False
    )

    # ========================================================
    # REQUIRED PAYMENT TRACKING FIELDS
    # ========================================================

    payment_method = Column(
        String(50),
        nullable=True
    )

    transaction_id = Column(
        String(255),
        nullable=True
    )

    status = Column(
        String(50),
        nullable=False,
        default="pending"
    )

    timestamp = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # ========================================================
    # STRIPE TRACKING
    # ========================================================

    payment_intent_id = Column(
        String(255),
        nullable=True
    )

    checkout_session_id = Column(
        String(255),
        nullable=True
    )

    # ========================================================
    # ORDER RELATIONSHIP
    # ========================================================

    order = relationship(
        "Order",
        back_populates="payment"
    )