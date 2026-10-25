from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Meter, Plan, PlanMeter


async def seed_catalog_if_empty(session: AsyncSession) -> None:
    existing = await session.scalar(select(Meter.id).limit(1))
    if existing is not None:
        return

    api_calls = Meter(
        code="api_calls",
        display_name="API requests",
        unit="request",
        description="Counted once per successful API call you meter in your product.",
    )
    tokens = Meter(
        code="tokens",
        display_name="Model tokens",
        unit="token",
        description="Sum of input and output tokens for LLM-style usage.",
    )
    session.add_all([api_calls, tokens])
    await session.flush()

    starter = Plan(
        code="starter",
        name="Starter",
        description="Included quota with per-unit overage on two meters.",
    )
    session.add(starter)
    await session.flush()

    session.add_all(
        [
            PlanMeter(
                plan_id=starter.id,
                meter_id=api_calls.id,
                included_quantity=Decimal("10000"),
                unit_price_cents=1,
            ),
            PlanMeter(
                plan_id=starter.id,
                meter_id=tokens.id,
                included_quantity=Decimal("100000"),
                unit_price_cents=1,
            ),
        ]
    )


def default_subscription_period() -> tuple[datetime, datetime]:
    start = datetime.now(UTC)
    end = start + timedelta(days=30)
    return start, end
