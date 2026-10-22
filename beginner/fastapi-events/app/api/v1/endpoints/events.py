from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_event_service
from app.schemas.event import (
    EventCreate,
    EventDetail,
    EventRead,
    EventStatus,
    EventUpdate,
    RegistrationCreate,
    RegistrationRead,
)
from app.services.event_service import EventService

router = APIRouter()


@router.get(
    "",
    response_model=list[EventRead],
    summary="List events",
    description=(
        "Sorted by `starts_at`. Filter with `status`, `starts_after`, `starts_before`, "
        "or search `q` in title and description."
    ),
)
def list_events(
    service: Annotated[EventService, Depends(get_event_service)],
    event_status: Annotated[
        EventStatus | None,
        Query(alias="status", description="scheduled or cancelled"),
    ] = None,
    starts_after: Annotated[
        datetime | None,
        Query(description="ISO datetime — include events starting at or after this instant"),
    ] = None,
    starts_before: Annotated[
        datetime | None,
        Query(description="ISO datetime — include events starting at or before this instant"),
    ] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> list[EventRead]:
    return service.list_events(
        status=event_status,
        starts_after=starts_after,
        starts_before=starts_before,
        q=q,
    )


@router.post(
    "",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a scheduled event",
)
def create_event(
    payload: EventCreate,
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventRead:
    return service.create_event(payload)


@router.get(
    "/{event_id}",
    response_model=EventDetail,
    summary="Event with registrations",
)
def get_event(
    event_id: int,
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventDetail:
    return service.get_event_detail(event_id)


@router.patch(
    "/{event_id}",
    response_model=EventRead,
    summary="Update an event",
)
def update_event(
    event_id: int,
    payload: EventUpdate,
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventRead:
    return service.update_event(event_id, payload)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an event",
    description="Removes the event and all registrations.",
)
def delete_event(
    event_id: int,
    service: Annotated[EventService, Depends(get_event_service)],
) -> None:
    service.delete_event(event_id)


@router.post(
    "/{event_id}/cancel",
    response_model=EventRead,
    summary="Cancel an event",
    responses={409: {"description": "Already cancelled."}},
)
def cancel_event(
    event_id: int,
    service: Annotated[EventService, Depends(get_event_service)],
) -> EventRead:
    return service.cancel_event(event_id)


@router.get(
    "/{event_id}/registrations",
    response_model=list[RegistrationRead],
    summary="List registrations",
)
def list_registrations(
    event_id: int,
    service: Annotated[EventService, Depends(get_event_service)],
) -> list[RegistrationRead]:
    return service.list_registrations(event_id)


@router.post(
    "/{event_id}/registrations",
    response_model=RegistrationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register for an event",
    responses={
        409: {
            "description": "Cancelled, full, or duplicate email.",
        }
    },
)
def register_for_event(
    event_id: int,
    payload: RegistrationCreate,
    service: Annotated[EventService, Depends(get_event_service)],
) -> RegistrationRead:
    return service.register(event_id, payload)
