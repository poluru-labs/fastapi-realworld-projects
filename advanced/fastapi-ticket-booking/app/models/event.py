from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EventStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default=EventStatus.DRAFT.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tiers: Mapped[list["TicketTier"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class TicketTier(Base):
    __tablename__ = "ticket_tiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    price_cents: Mapped[int] = mapped_column()
    capacity: Mapped[int] = mapped_column()
    quantity_sold: Mapped[int] = mapped_column(default=0)

    event: Mapped[Event] = relationship(back_populates="tiers")
