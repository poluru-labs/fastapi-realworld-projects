from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    CANCELED = "canceled"


class InvoiceStatus(StrEnum):
    OPEN = "open"
    PAID = "paid"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    api_key_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="customer")
    usage_events: Mapped[list["UsageEvent"]] = relationship(back_populates="customer")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="customer")


class Meter(Base):
    __tablename__ = "meters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text, default="")

    plan_meters: Mapped[list["PlanMeter"]] = relationship(back_populates="meter")
    usage_events: Mapped[list["UsageEvent"]] = relationship(back_populates="meter")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")

    plan_meters: Mapped[list["PlanMeter"]] = relationship(back_populates="plan")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")


class PlanMeter(Base):
    __tablename__ = "plan_meters"
    __table_args__ = (UniqueConstraint("plan_id", "meter_id", name="uq_plan_meter"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"))
    meter_id: Mapped[int] = mapped_column(ForeignKey("meters.id", ondelete="CASCADE"))
    included_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    unit_price_cents: Mapped[int] = mapped_column(default=0)

    plan: Mapped["Plan"] = relationship(back_populates="plan_meters")
    meter: Mapped["Meter"] = relationship(back_populates="plan_meters")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        index=True,
    )
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(32), default=SubscriptionStatus.ACTIVE.value)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    customer: Mapped["Customer"] = relationship(back_populates="subscriptions")
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")


class UsageEvent(Base):
    __tablename__ = "usage_events"
    __table_args__ = (
        UniqueConstraint("customer_id", "idempotency_key", name="uq_usage_idempotency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        index=True,
    )
    meter_id: Mapped[int] = mapped_column(
        ForeignKey("meters.id", ondelete="RESTRICT"),
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    customer: Mapped["Customer"] = relationship(back_populates="usage_events")
    meter: Mapped["Meter"] = relationship(back_populates="usage_events")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        index=True,
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    total_cents: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(32), default=InvoiceStatus.OPEN.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    customer: Mapped["Customer"] = relationship(back_populates="invoices")
    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
    )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"),
        index=True,
    )
    meter_id: Mapped[int] = mapped_column(ForeignKey("meters.id", ondelete="RESTRICT"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    included_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    billable_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    unit_price_cents: Mapped[int]
    amount_cents: Mapped[int]

    invoice: Mapped["Invoice"] = relationship(back_populates="lines")
    meter: Mapped["Meter"] = relationship()
