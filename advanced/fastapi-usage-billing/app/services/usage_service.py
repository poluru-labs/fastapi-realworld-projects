from datetime import UTC, datetime
from decimal import Decimal

from app.core.exceptions import NotFoundError
from app.core.logging import request_id_var
from app.models.billing import UsageEvent
from app.repositories.billing_repository import BillingRepository
from app.schemas.usage import UsageEventCreate, UsageEventRead, UsageMeterTotal, UsageSummaryRead


class UsageService:
    def __init__(self, repo: BillingRepository) -> None:
        self._repo = repo

    async def ingest_event(self, customer_id: int, payload: UsageEventCreate) -> UsageEventRead:
        existing = await self._repo.get_usage_event_by_idempotency(
            customer_id,
            payload.idempotency_key,
        )
        if existing is not None:
            meter = await self._repo.get_meter_by_id(existing.meter_id)
            code = meter.code if meter is not None else "unknown"
            return self._to_read(existing, code)

        meter = await self._repo.get_meter_by_code(payload.meter_code)
        if meter is None:
            raise NotFoundError("Meter", payload.meter_code)

        recorded_at = payload.recorded_at or datetime.now(UTC)
        event = UsageEvent(
            customer_id=customer_id,
            meter_id=meter.id,
            quantity=payload.quantity,
            idempotency_key=payload.idempotency_key,
            recorded_at=recorded_at,
            request_id=request_id_var.get() if request_id_var.get() != "-" else None,
        )
        created = await self._repo.add_usage_event(event)
        return self._to_read(created, meter.code)

    async def usage_summary(self, customer_id: int) -> UsageSummaryRead:
        subscription = await self._repo.get_active_subscription(customer_id)
        if subscription is None:
            raise NotFoundError("Subscription", customer_id)
        totals = await self._repo.sum_usage(
            customer_id,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
        )
        return UsageSummaryRead(
            customer_id=customer_id,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            totals=[UsageMeterTotal(meter_code=code, quantity=qty) for code, qty in totals],
        )

    def _to_read(self, event: UsageEvent, meter_code: str) -> UsageEventRead:
        return UsageEventRead(
            id=event.id,
            customer_id=event.customer_id,
            meter_code=meter_code,
            quantity=Decimal(str(event.quantity)),
            idempotency_key=event.idempotency_key,
            recorded_at=event.recorded_at,
            request_id=event.request_id,
        )
