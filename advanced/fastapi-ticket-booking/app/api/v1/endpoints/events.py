from fastapi import APIRouter, status

from app.api.deps import AdminUser, AppSettings, DbSession, OptionalUser
from app.schemas.event import EventCreate, EventRead, TierCreate, TierRead
from app.schemas.venue import VenueCreate, VenueRead
from app.services.event_service import EventService

router = APIRouter(tags=["events"])


@router.get("/venues", response_model=list[VenueRead], summary="List venues")
async def list_venues(session: DbSession, settings: AppSettings) -> list[VenueRead]:
    return await EventService(session, settings).list_venues()


@router.post(
    "/venues",
    response_model=VenueRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a venue (admin)",
)
async def create_venue(
    payload: VenueCreate,
    actor: AdminUser,
    session: DbSession,
    settings: AppSettings,
) -> VenueRead:
    return await EventService(session, settings).create_venue(actor, payload)


@router.get("/events", response_model=list[EventRead], summary="List events")
async def list_events(
    session: DbSession,
    settings: AppSettings,
    actor: OptionalUser,
) -> list[EventRead]:
    return await EventService(session, settings).list_events(actor)


@router.get(
    "/events/{slug}",
    response_model=EventRead,
    summary="Event detail with live availability",
)
async def get_event(
    slug: str,
    session: DbSession,
    settings: AppSettings,
    actor: OptionalUser,
) -> EventRead:
    return await EventService(session, settings).get_event(actor, slug)


@router.post(
    "/events",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft event (admin)",
)
async def create_event(
    payload: EventCreate,
    actor: AdminUser,
    session: DbSession,
    settings: AppSettings,
) -> EventRead:
    return await EventService(session, settings).create_event(actor, payload)


@router.post(
    "/events/{event_id}/tiers",
    response_model=TierRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a ticket tier (admin, draft only)",
)
async def add_tier(
    event_id: int,
    payload: TierCreate,
    actor: AdminUser,
    session: DbSession,
    settings: AppSettings,
) -> TierRead:
    return await EventService(session, settings).add_tier(actor, event_id, payload)


@router.post("/events/{slug}/publish", response_model=EventRead, summary="Publish event (admin)")
async def publish_event(
    slug: str,
    actor: AdminUser,
    session: DbSession,
    settings: AppSettings,
) -> EventRead:
    return await EventService(session, settings).publish_event(actor, slug)
