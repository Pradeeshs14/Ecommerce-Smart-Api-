
from datetime import datetime

from pydantic import BaseModel  # type: ignore


# ============================================================
# RETURN REQUEST CREATE
# ============================================================

class ReturnRequestCreate(BaseModel):

    reason: str

    comment: str | None = None


# ============================================================
# RETURN REQUEST RESPONSE
# ============================================================

class ReturnRequestResponse(BaseModel):

    id: int

    order_id: int

    user_id: int

    reason: str

    comment: str | None

    status: str

    created_at: datetime

    class Config:
        from_attributes = True

