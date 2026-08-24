from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    type = Column(
        String(50),
        nullable=False
    )

    message = Column(
        String(255),
        nullable=False
    )

    read_status = Column(
        String(20),
        nullable=False,
        default="unread"
    )

    timestamp = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    user = relationship(
        "User",
        back_populates="notifications"
    )