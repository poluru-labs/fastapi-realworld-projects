from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class HoldStatus(StrEnum):
    ACTIVE = "active"
    CONSUMED = "consumed"
    RELEASED = "released"
    EXPIRED = "expired"


class TicketHold(Base):
    __tablename__ = "ticket_holds"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    tier_id: Mapped[int] = mapped_column(
        ForeignKey("ticket_tiers.id", ondelete="CASCADE"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default=HoldStatus.ACTIVE.value)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
