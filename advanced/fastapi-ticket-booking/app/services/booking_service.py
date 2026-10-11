"""Checkout from holds and idempotent confirmation live here."""

import secrets
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.booking import Booking, BookingItem
from app.models.booking import BookingStatus as ModelBookingStatus
from app.models.hold import HoldStatus as ModelHoldStatus
from app.models.idempotency import IdempotencyRecord
from app.repositories.booking_repository import BookingRepository
from app.repositories.event_repository import EventRepository
from app.repositories.hold_repository import HoldRepository
from app.repositories.idempotency_repository import IdempotencyRepository
from app.schemas.booking import BookingCreate, BookingItemRead, BookingRead, BookingStatus
from app.schemas.user import UserRead, UserRole


class BookingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._bookings = BookingRepository(session)
        self._holds = HoldRepository(session)
        self._events = EventRepository(session)
        self._idempotency = IdempotencyRepository(session)

    async def list_bookings(self, actor: UserRead) -> list[BookingRead]:
        if actor.role is UserRole.ADMIN:
            rows = await self._bookings.list_all()
        else:
            rows = await self._bookings.list_for_user(actor.id)
        return [await self._to_read(row) for row in rows]

    async def get_booking(self, actor: UserRead, booking_id: int) -> BookingRead:
        row = await self._bookings.get_with_items(booking_id)
        if row is None or not self._can_view(actor, row.user_id):
            raise NotFoundError("Booking", booking_id)
        return await self._to_read(row)

    async def confirm(
        self,
        actor: UserRead,
        payload: BookingCreate,
        *,
        idempotency_key: str,
    ) -> BookingRead:
        cached = await self._idempotency.get(idempotency_key)
        if cached is not None:
            if cached.user_id != actor.id:
                raise ConflictError("Idempotency key belongs to another user")
            return BookingRead.model_validate_json(cached.response_json)

        await self._holds.expire_stale()
        hold = await self._holds.get(payload.hold_id)
        if hold is None or hold.user_id != actor.id:
            raise NotFoundError("Hold", payload.hold_id)
        if hold.status != ModelHoldStatus.ACTIVE.value:
            raise ConflictError("Hold is not active")
        expires_at = hold.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            hold.status = ModelHoldStatus.EXPIRED.value
            await self._holds.save(hold)
            await self._session.commit()
            raise ConflictError("Hold expired — create a new hold")

        tier = await self._events.get_tier(hold.tier_id)
        if tier is None:
            raise NotFoundError("TicketTier", hold.tier_id)
        event = await self._events.get_by_id(tier.event_id)
        if event is None:
            raise NotFoundError("Event", tier.event_id)

        total = tier.price_cents * hold.quantity
        code = secrets.token_hex(4).upper()
        booking = Booking(
            user_id=actor.id,
            event_id=event.id,
            hold_id=hold.id,
            confirmation_code=code,
            status=ModelBookingStatus.CONFIRMED.value,
            total_cents=total,
            items=[
                BookingItem(
                    tier_id=tier.id,
                    quantity=hold.quantity,
                    unit_price_cents=tier.price_cents,
                )
            ],
        )
        tier.quantity_sold += hold.quantity
        hold.status = ModelHoldStatus.CONSUMED.value

        await self._bookings.add(booking)
        response = await self._to_read(booking)
        await self._idempotency.save(
            IdempotencyRecord(
                key=idempotency_key,
                user_id=actor.id,
                response_json=response.model_dump_json(),
                status_code=201,
            )
        )
        await self._session.commit()
        refreshed = await self._bookings.get_with_items(booking.id)
        assert refreshed is not None
        return await self._to_read(refreshed)

    async def cancel(self, actor: UserRead, booking_id: int) -> BookingRead:
        booking = await self._bookings.get_with_items(booking_id)
        if booking is None or not self._can_view(actor, booking.user_id):
            raise NotFoundError("Booking", booking_id)
        if booking.status == ModelBookingStatus.CANCELLED.value:
            raise ConflictError("Booking already cancelled")

        event = await self._events.get_by_id(booking.event_id)
        if event is None:
            raise NotFoundError("Event", booking.event_id)
        starts = event.starts_at
        if starts.tzinfo is None:
            starts = starts.replace(tzinfo=UTC)
        if starts <= datetime.now(UTC):
            raise ConflictError("Cannot cancel after the event has started")

        for item in booking.items:
            tier = await self._events.get_tier(item.tier_id)
            if tier is not None:
                tier.quantity_sold = max(0, tier.quantity_sold - item.quantity)

        booking.status = ModelBookingStatus.CANCELLED.value
        await self._session.commit()
        refreshed = await self._bookings.get_with_items(booking.id)
        assert refreshed is not None
        return await self._to_read(refreshed)

    @staticmethod
    def _can_view(actor: UserRead, owner_id: int) -> bool:
        if actor.role is UserRole.ADMIN:
            return True
        return actor.id == owner_id

    async def _to_read(self, booking: Booking) -> BookingRead:
        event = await self._events.get_by_id(booking.event_id)
        items: list[BookingItemRead] = []
        for item in booking.items:
            tier = await self._events.get_tier(item.tier_id)
            items.append(
                BookingItemRead(
                    tier_id=item.tier_id,
                    tier_name=tier.name if tier else "Unknown",
                    quantity=item.quantity,
                    unit_price_cents=item.unit_price_cents,
                    line_total_cents=item.quantity * item.unit_price_cents,
                )
            )
        return BookingRead(
            id=booking.id,
            confirmation_code=booking.confirmation_code,
            event_slug=event.slug if event else "unknown",
            event_title=event.title if event else "Unknown",
            status=BookingStatus(booking.status),
            total_cents=booking.total_cents,
            items=items,
            created_at=booking.created_at,
        )
