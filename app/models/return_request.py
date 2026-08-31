from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String # type: ignore
from sqlalchemy.orm import relationship # type: ignore

from app.core.database import Base


class ReturnRequest(Base):

    __tablename__ = "return_requests"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    order_id = Column(
        Integer,
        ForeignKey("orders.id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    reason = Column(
        String(255),
        nullable=False
    )

    comment = Column(
        String(500),
        nullable=True
    )

    status = Column(
        String(50),
        nullable=False,
        default="pending"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    order = relationship(
        "Order",
        back_populates="return_requests"
    )

    user = relationship(
        "User"
    )