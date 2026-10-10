from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import (
    get_current_user,
    get_event_service,
    get_optional_user,
    get_registration_service,
)
from app.schemas.event import EventCreate, EventRead, EventStatus, EventUpdate
from app.schemas.registration import RegistrationRead
from app.schemas.user import UserRead
from app.services.event_service import EventService
from app.services.registration_service import RegistrationService

router = APIRouter()

_CREATE_EXAMPLES = {
    "meetup": {
        "summary": "Community meetup",
        "value": {
            "title": "FastAPI Office Hours",
            "summary": "Bring your routing questions.",
            "description": "Round-table Q&A with volunteers.",
            "location": "Room 204",
            "starts_at": "2026-12-10T17:00:00+00:00",
            "ends_at": "2026-12-10T19:00:00+00:00",
            "capacity": 30,
            "tags": ["fastapi", "office-hours"],
        },
    }
}


@router.get(
    "",
    response_model=list[EventRead],
    summary="List events",
    description=(
        "Anonymous callers see **published** events only. "
        "Platform admins may pass `status` to include drafts or cancelled rows."
    ),
)
def list_events(
    service: Annotated[EventService, Depends(get_event_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
    event_status: Annotated[
        EventStatus | None,
        Query(alias="status", description="Admin-only filter for draft, published, or cancelled."),
    ] = None,
    tag: Annotated[str | None, Query(description="Filter by tag on published events.")] = None,
    query: Annotated[
        str | None,
        Query(description="Case-insensitive search in title, summary, or location."),
    ] = None,
) -> list[EventRead]:
    return service.list_events(actor, status=event_status, tag=tag, query=query)


@router.get(
    "/{slug}",
    response_model=EventRead,
    summary="Get one event",
    description=(
        "Published events are public. Draft and cancelled events return **404** for everyone "
        "except a platform admin."
    ),
)
def get_event(
    slug: str,
    service: Annotated[EventService, Depends(get_event_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
) -> EventRead:
    return service.get_event(actor, slug)


@router.post(
    "",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft event (admin)",
)
def create_event(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EventService, Depends(get_event_service)],
    payload: Annotated[EventCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> EventRead:
    return service.create_event(actor, payload)


@router.patch(
    "/{slug}",
    response_model=EventRead,
    summary="Update a draft event (admin)",
    description=(
        "Only **draft** events accept content edits. "
        "Capacity cannot drop below registered count."
    ),
)
def update_event(
    slug: str,
    payload: EventUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventRead:
    return service.update_event(actor, slug, payload)


@router.post(
    "/{slug}/publish",
    response_model=EventRead,
    summary="Publish a draft event (admin)",
)
def publish_event(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventRead:
    return service.transition(actor, slug, EventStatus.PUBLISHED)


@router.post(
    "/{slug}/unpublish",
    response_model=EventRead,
    summary="Return a published event to draft (admin)",
    description="Blocked with **409** while registrations or waitlist entries exist.",
)
def unpublish_event(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventRead:
    return service.transition(actor, slug, EventStatus.DRAFT)


@router.post(
    "/{slug}/cancel",
    response_model=EventRead,
    summary="Cancel an event (admin)",
    description="Cancels the event and every active registration.",
)
def cancel_event(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventRead:
    return service.transition(actor, slug, EventStatus.CANCELLED)


@router.get(
    "/{slug}/registrations",
    response_model=list[RegistrationRead],
    summary="List registrations for an event (admin)",
)
def list_event_registrations(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[RegistrationService, Depends(get_registration_service)],
) -> list[RegistrationRead]:
    return service.list_for_event_slug(actor, slug)
