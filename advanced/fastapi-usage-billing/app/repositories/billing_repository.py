from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing import (
    Customer,
    Invoice,
    InvoiceLine,
    Meter,
    Plan,
    PlanMeter,
    Subscription,
    SubscriptionStatus,
    UsageEvent,
)


class BillingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_customer(self, customer: Customer) -> Customer:
        self._session.add(customer)
        await self._session.flush()
        return customer

    async def get_customer(self, customer_id: int) -> Customer | None:
        return await self._session.get(Customer, customer_id)

    async def get_customer_by_external_id(self, external_id: str) -> Customer | None:
        stmt = select(Customer).where(Customer.external_id == external_id)
        return await self._session.scalar(stmt)

    async def get_customer_by_api_key_hash(self, api_key_hash: str) -> Customer | None:
        stmt = select(Customer).where(Customer.api_key_hash == api_key_hash)
        return await self._session.scalar(stmt)

    async def list_customers(self) -> list[Customer]:
        stmt = select(Customer).order_by(Customer.id)
        return list(await self._session.scalars(stmt))

    async def list_meters(self) -> list[Meter]:
        stmt = select(Meter).order_by(Meter.code)
        return list(await self._session.scalars(stmt))

    async def get_meter_by_code(self, code: str) -> Meter | None:
        stmt = select(Meter).where(Meter.code == code)
        return await self._session.scalar(stmt)

    async def get_meter_by_id(self, meter_id: int) -> Meter | None:
        return await self._session.get(Meter, meter_id)

    async def list_plans(self) -> list[Plan]:
        stmt = (
            select(Plan)
            .options(selectinload(Plan.plan_meters).selectinload(PlanMeter.meter))
            .order_by(Plan.code)
        )
        return list(await self._session.scalars(stmt))

    async def get_plan_by_code(self, code: str) -> Plan | None:
        stmt = (
            select(Plan)
            .where(Plan.code == code)
            .options(selectinload(Plan.plan_meters).selectinload(PlanMeter.meter))
        )
        return await self._session.scalar(stmt)

    async def add_subscription(self, subscription: Subscription) -> Subscription:
        self._session.add(subscription)
        await self._session.flush()
        return subscription

    async def get_active_subscription(self, customer_id: int) -> Subscription | None:
        stmt = (
            select(Subscription)
            .where(
                Subscription.customer_id == customer_id,
                Subscription.status == SubscriptionStatus.ACTIVE.value,
            )
            .options(
                selectinload(Subscription.plan)
                .selectinload(Plan.plan_meters)
                .selectinload(PlanMeter.meter)
            )
            .order_by(Subscription.id.desc())
            .limit(1)
        )
        return await self._session.scalar(stmt)

    async def get_usage_event_by_idempotency(
        self,
        customer_id: int,
        idempotency_key: str,
    ) -> UsageEvent | None:
        stmt = select(UsageEvent).where(
            UsageEvent.customer_id == customer_id,
            UsageEvent.idempotency_key == idempotency_key,
        )
        return await self._session.scalar(stmt)

    async def add_usage_event(self, event: UsageEvent) -> UsageEvent:
        self._session.add(event)
        await self._session.flush()
        return event

    async def sum_usage(
        self,
        customer_id: int,
        *,
        period_start: datetime,
        period_end: datetime,
    ) -> list[tuple[str, Decimal]]:
        stmt = (
            select(Meter.code, func.coalesce(func.sum(UsageEvent.quantity), 0))
            .join(Meter, Meter.id == UsageEvent.meter_id)
            .where(
                UsageEvent.customer_id == customer_id,
                UsageEvent.recorded_at >= period_start,
                UsageEvent.recorded_at < period_end,
            )
            .group_by(Meter.code)
            .order_by(Meter.code)
        )
        rows = await self._session.execute(stmt)
        return [(code, Decimal(str(total))) for code, total in rows.all()]

    async def add_invoice(self, invoice: Invoice) -> Invoice:
        self._session.add(invoice)
        await self._session.flush()
        return invoice

    async def list_invoices(self, customer_id: int) -> list[Invoice]:
        stmt = (
            select(Invoice)
            .where(Invoice.customer_id == customer_id)
            .options(selectinload(Invoice.lines).selectinload(InvoiceLine.meter))
            .order_by(Invoice.id.desc())
        )
        return list(await self._session.scalars(stmt))

    async def invoice_for_period(
        self,
        customer_id: int,
        period_start: datetime,
        period_end: datetime,
    ) -> Invoice | None:
        stmt = select(Invoice).where(
            Invoice.customer_id == customer_id,
            Invoice.period_start == period_start,
            Invoice.period_end == period_end,
        )
        return await self._session.scalar(stmt)
