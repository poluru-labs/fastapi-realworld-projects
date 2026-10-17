from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.delivery_repository import DeliveryRepository
from app.repositories.relay_repository import RelayRepository
from app.schemas.chat import (
    ClaimDeliveryRequest,
    CompleteDeliveryRequest,
    DeliveryRead,
    OutboxStatus,
    RelayHeartbeat,
    RelayRegister,
)
from app.schemas.user import UserRead, UserRole


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class DeliveryService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._deliveries = DeliveryRepository(session)
        self._relays = RelayRepository(session)

    async def register_relay(self, actor: UserRead, payload: RelayRegister) -> dict[str, str]:
        now = datetime.now(UTC)
        await self._relays.upsert(
            relay_id=payload.relay_id,
            registered_by_id=actor.id,
            room_slugs=payload.room_slugs,
            now=now,
        )
        await self._session.commit()
        return {"relay_id": payload.relay_id, "status": "registered"}

    async def heartbeat(self, actor: UserRead, payload: RelayHeartbeat) -> dict[str, str]:
        node = await self._relays.get(payload.relay_id)
        if node is None:
            raise NotFoundError("Relay", payload.relay_id)
        if actor.role is not UserRole.ADMIN and node.registered_by_id != actor.id:
            raise ForbiddenError("You can only heartbeat relays you registered")
        await self._relays.heartbeat(payload.relay_id, datetime.now(UTC))
        await self._session.commit()
        return {"relay_id": payload.relay_id, "status": "ok"}

    async def claim(self, actor: UserRead, payload: ClaimDeliveryRequest) -> DeliveryRead:
        node = await self._relays.get(payload.relay_id)
        if node is None:
            raise NotFoundError("Relay", payload.relay_id)
        if actor.role is not UserRole.ADMIN and node.registered_by_id != actor.id:
            raise ForbiddenError("You can only claim with relays you registered")

        now = datetime.now(UTC)
        row = await self._deliveries.find_claimable(room_slugs=list(node.room_slugs), now=now)
        if row is None:
            raise NotFoundError("ClaimableDelivery", "none")

        lease = timedelta(seconds=self._settings.relay_lease_seconds)
        row.status = OutboxStatus.DELIVERING.value
        row.lease_holder = payload.relay_id
        row.lease_expires_at = now + lease
        row.version += 1
        await self._deliveries.save()
        await self._session.commit()
        return DeliveryRead.model_validate(row)

    async def complete(
        self,
        actor: UserRead,
        delivery_id: int,
        payload: CompleteDeliveryRequest,
    ) -> DeliveryRead:
        row = await self._deliveries.get(delivery_id)
        if row is None:
            raise NotFoundError("Delivery", delivery_id)
        node = await self._relays.get(payload.relay_id)
        if node is None:
            raise NotFoundError("Relay", payload.relay_id)
        if actor.role is not UserRole.ADMIN and node.registered_by_id != actor.id:
            raise ForbiddenError("You can only complete deliveries with relays you registered")

        if row.status != OutboxStatus.DELIVERING.value:
            raise ConflictError("Delivery is not in delivering state")
        if row.lease_holder != payload.relay_id:
            raise ForbiddenError("This relay does not hold the lease for this delivery")
        now = datetime.now(UTC)
        lease_expires = _as_utc(row.lease_expires_at)
        if lease_expires is not None and lease_expires < now:
            raise ConflictError("Lease expired; delivery may be reclaimed")
        if row.version != payload.expected_version:
            raise ConflictError(
                f"Stale version: expected {payload.expected_version}, current is {row.version}"
            )

        row.status = OutboxStatus.DELIVERED.value
        row.delivered_at = now
        row.lease_holder = None
        row.lease_expires_at = None
        row.version += 1
        await self._deliveries.save()
        await self._session.commit()
        return DeliveryRead.model_validate(row)
