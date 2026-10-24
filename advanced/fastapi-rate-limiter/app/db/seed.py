from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.client_tokens import hash_client_key
from app.core.windows import fixed_window_start
from app.models.rate_limiting import RateLimitClient, RateLimitCounter, RateLimitPolicy
from app.schemas.rate_limiting import PolicyStatus

SEED_CLIENT_KEY = "seed-client-mobile-app"


async def seed_reference_data(session: AsyncSession) -> None:
    existing = await session.scalar(
        select(RateLimitPolicy).where(RateLimitPolicy.key == "public-api")
    )
    if existing is not None:
        return

    now = datetime.now(UTC)
    policy = RateLimitPolicy(
        key="public-api",
        name="Public API",
        description="Default fixed window for mobile and web clients.",
        limit=10,
        window_seconds=60,
        status=PolicyStatus.ACTIVE.value,
        created_at=now,
        updated_at=now,
    )
    session.add(policy)
    await session.flush()

    client = RateLimitClient(
        key="mobile-app",
        name="Mobile app backend",
        policy_id=policy.id,
        client_key_hash=hash_client_key(SEED_CLIENT_KEY),
        created_at=now,
    )
    session.add(client)
    await session.flush()

    window_start = fixed_window_start(now, policy.window_seconds)
    session.add(
        RateLimitCounter(
            client_id=client.id,
            subject_key="device-abc",
            window_start=window_start,
            count=3,
        )
    )
    await session.commit()
