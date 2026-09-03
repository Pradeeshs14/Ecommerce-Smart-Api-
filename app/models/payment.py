from datetime import datetime

from sqlalchemy import ( # type: ignore
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)  # type: ignore

from sqlalchemy.orm import relationship  # type: ignore

from app.core.database import Base


# ============================================================
# PAYMENT MODEL
# ============================================================

class Payment(Base):

    __tablename__ = "payments"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # ORDER REFERENCE
    # ========================================================

    order_id = Column(
        Integer,
        ForeignKey("orders.id"),
        nullable=False,
        unique=True,
    )

    # ========================================================
    # PAYMENT AMOUNT
    # ========================================================

    amount = Column(
        Float,
        nullable=False,
    )

    # ========================================================
    # PAYMENT METHOD
    # ========================================================

    payment_method = Column(
        String(50),
        nullable=True,
    )

    # ========================================================
    # TRANSACTION ID
    # ========================================================

    transaction_id = Column(
        String(255),
        nullable=True,
    )

    # ========================================================
    # PAYMENT STATUS
    # ========================================================

    status = Column(
        String(50),
        nullable=False,
        default="pending",
    )

    # ========================================================
    # PAYMENT TIMESTAMP
    # ========================================================

    timestamp = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # ========================================================
    # STRIPE PAYMENT INTENT
    # ========================================================

    payment_intent_id = Column(
        String(255),
        nullable=True,
    )

    # ========================================================
    # STRIPE CHECKOUT SESSION
    # ========================================================

    checkout_session_id = Column(
        String(255),
        nullable=True,
    )

    # ========================================================
    # STRIPE REFUND ID
    # ========================================================

    refund_id = Column(
        String(255),
        nullable=True,
    )

    # ========================================================
    # ORDER RELATIONSHIP
    # ========================================================

    order = relationship(
        "Order",
        back_populates="payment",
    )