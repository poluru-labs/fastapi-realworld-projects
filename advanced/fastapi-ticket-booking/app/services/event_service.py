"""Event visibility and admin publishing rules live here."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.event import Event, TicketTier
from app.models.event import EventStatus as ModelEventStatus
from app.repositories.event_repository import EventRepository
from app.repositories.hold_repository import HoldRepository
from app.repositories.venue_repository import VenueRepository
from app.schemas.event import EventCreate, EventRead, EventStatus, TierCreate, TierRead, slugify
from app.schemas.user import UserRead, UserRole
from app.schemas.venue import VenueCreate, VenueRead


def _can_view(actor: UserRead | None, event: Event) -> bool:
    if event.status == ModelEventStatus.PUBLISHED.value:
        return True
    if actor is None:
        return False
    return actor.role is UserRole.ADMIN


class EventService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._events = EventRepository(session)
        self._venues = VenueRepository(session)
        self._holds = HoldRepository(session)

    async def list_venues(self) -> list[VenueRead]:
        rows = await self._venues.list_all()
        return [VenueRead.model_validate(row) for row in rows]

    async def create_venue(self, actor: UserRead, payload: VenueCreate) -> VenueRead:
        self._require_admin(actor)
        venue = await self._venues.create(name=payload.name, city=payload.city)
        await self._session.commit()
        return VenueRead.model_validate(venue)

    async def list_events(self, actor: UserRead | None) -> list[EventRead]:
        await self._holds.expire_stale()
        rows = await self._events.list_all()
        if actor is None or actor.role is not UserRole.ADMIN:
            rows = [event for event in rows if event.status == ModelEventStatus.PUBLISHED.value]
        result: list[EventRead] = []
        for event in rows:
            venue = await self._venues.get(event.venue_id)
            result.append(
                await self._to_read(
                    event,
                    venue_name=venue.name if venue else "Unknown",
                    city=venue.city if venue else "",
                )
            )
        return result

    async def get_event(self, actor: UserRead | None, slug: str) -> EventRead:
        await self._holds.expire_stale()
        event = await self._events.get_by_slug(slug)
        if event is None or not _can_view(actor, event):
            raise NotFoundError("Event", slug)
        venue = await self._venues.get(event.venue_id)
        return await self._to_read(
            event,
            venue_name=venue.name if venue else "Unknown",
            city=venue.city if venue else "",
        )

    async def create_event(self, actor: UserRead, payload: EventCreate) -> EventRead:
        self._require_admin(actor)
        venue = await self._venues.get(payload.venue_id)
        if venue is None:
            raise NotFoundError("Venue", payload.venue_id)
        slug = payload.slug or slugify(payload.title)
        if not slug:
            raise ConflictError("Could not derive slug from title")
        if await self._events.slug_taken(slug):
            raise ConflictError("Slug already in use")
        event = Event(
            slug=slug,
            title=payload.title,
            description=payload.description,
            venue_id=payload.venue_id,
            starts_at=payload.starts_at,
            status=ModelEventStatus.DRAFT.value,
        )
        await self._events.add(event)
        await self._session.commit()
        return await self._to_read(event, venue_name=venue.name, city=venue.city)

    async def add_tier(self, actor: UserRead, event_id: int, payload: TierCreate) -> TierRead:
        self._require_admin(actor)
        event = await self._events.get_by_id(event_id)
        if event is None:
            raise NotFoundError("Event", event_id)
        if event.status != ModelEventStatus.DRAFT.value:
            raise ConflictError("Tiers can only be added while the event is a draft")
        tier = TicketTier(
            event_id=event_id,
            name=payload.name,
            price_cents=payload.price_cents,
            capacity=payload.capacity,
        )
        await self._events.add_tier(tier)
        await self._session.commit()
        held = await self._holds.active_quantity_for_tier(tier.id)
        return self._tier_read(tier, held=held)

    async def publish_event(self, actor: UserRead, slug: str) -> EventRead:
        self._require_admin(actor)
        event = await self._events.get_by_slug(slug)
        if event is None:
            raise NotFoundError("Event", slug)
        if event.status != ModelEventStatus.DRAFT.value:
            raise ConflictError("Only draft events can be published")
        if not event.tiers:
            raise ConflictError("Add at least one ticket tier before publishing")
        event.status = ModelEventStatus.PUBLISHED.value
        await self._session.commit()
        venue = await self._venues.get(event.venue_id)
        return await self._to_read(
            event,
            venue_name=venue.name if venue else "Unknown",
            city=venue.city if venue else "",
        )

    async def _to_read(self, event: Event, *, venue_name: str, city: str) -> EventRead:
        tiers: list[TierRead] = []
        for tier in event.tiers:
            held = await self._holds.active_quantity_for_tier(tier.id)
            tiers.append(self._tier_read(tier, held=held))
        return EventRead(
            id=event.id,
            slug=event.slug,
            title=event.title,
            description=event.description,
            venue_id=event.venue_id,
            venue_name=venue_name,
            city=city,
            starts_at=event.starts_at,
            status=EventStatus(event.status),
            tiers=tiers,
            created_at=event.created_at,
        )

    @staticmethod
    def _tier_read(tier: TicketTier, *, held: int) -> TierRead:
        available = max(0, tier.capacity - tier.quantity_sold - held)
        return TierRead(
            id=tier.id,
            name=tier.name,
            price_cents=tier.price_cents,
            capacity=tier.capacity,
            quantity_sold=tier.quantity_sold,
            quantity_held=held,
            quantity_available=available,
        )

    @staticmethod
    def _require_admin(actor: UserRead) -> None:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Admin role required")
