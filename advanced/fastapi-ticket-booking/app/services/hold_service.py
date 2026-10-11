from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError
from app.models.event import EventStatus as ModelEventStatus
from app.models.hold import HoldStatus as ModelHoldStatus
from app.models.hold import TicketHold
from app.repositories.event_repository import EventRepository
from app.repositories.hold_repository import HoldRepository
from app.schemas.hold import HoldCreate, HoldRead, HoldStatus
from app.schemas.user import UserRead


class HoldService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._holds = HoldRepository(session)
        self._events = EventRepository(session)

    async def list_mine(self, actor: UserRead) -> list[HoldRead]:
        await self._holds.expire_stale()
        rows = await self._holds.list_active_for_user(actor.id)
        return [await self._to_read(row) for row in rows]

    async def create_hold(self, actor: UserRead, payload: HoldCreate) -> HoldRead:
        await self._holds.expire_stale()
        tier = await self._events.get_tier(payload.tier_id)
        if tier is None:
            raise NotFoundError("TicketTier", payload.tier_id)
        event = await self._events.get_by_id(tier.event_id)
        if event is None or event.status != ModelEventStatus.PUBLISHED.value:
            raise ConflictError("Tickets are not on sale for this tier")

        held = await self._holds.active_quantity_for_tier(tier.id)
        available = tier.capacity - tier.quantity_sold - held
        if payload.quantity > available:
            raise ConflictError("Not enough tickets available")

        expires_at = datetime.now(UTC) + timedelta(minutes=self._settings.hold_ttl_minutes)
        hold = TicketHold(
            user_id=actor.id,
            tier_id=tier.id,
            quantity=payload.quantity,
            status=ModelHoldStatus.ACTIVE.value,
            expires_at=expires_at,
        )
        await self._holds.add(hold)
        await self._session.commit()
        return await self._to_read(hold)

    async def release_hold(self, actor: UserRead, hold_id: int) -> HoldRead:
        hold = await self._holds.get(hold_id)
        if hold is None or hold.user_id != actor.id:
            raise NotFoundError("Hold", hold_id)
        if hold.status != ModelHoldStatus.ACTIVE.value:
            raise ConflictError("Hold is not active")
        hold.status = ModelHoldStatus.RELEASED.value
        await self._holds.save(hold)
        await self._session.commit()
        return await self._to_read(hold)

    async def _to_read(self, hold: TicketHold) -> HoldRead:
        tier = await self._events.get_tier(hold.tier_id)
        event = await self._events.get_by_id(tier.event_id) if tier else None
        return HoldRead(
            id=hold.id,
            tier_id=hold.tier_id,
            tier_name=tier.name if tier else "Unknown",
            event_slug=event.slug if event else "unknown",
            event_title=event.title if event else "Unknown",
            quantity=hold.quantity,
            status=HoldStatus(hold.status),
            expires_at=hold.expires_at,
            created_at=hold.created_at,
        )
