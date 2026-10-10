from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_current_user, get_registration_service
from app.schemas.registration import RegistrationCreate, RegistrationRead, RegistrationStatus
from app.schemas.user import UserRead
from app.services.registration_service import RegistrationService

router = APIRouter()

_REGISTER_EXAMPLES = {
    "meetup": {
        "summary": "Join a published event",
        "description": (
            "When capacity is full you land on the waitlist (`waitlisted`). "
            "Duplicate active registrations return **409**."
        ),
        "value": {"event_slug": "fastapi-meetup"},
    }
}


@router.get(
    "",
    response_model=list[RegistrationRead],
    summary="List registrations",
    description=(
        "Signed-in users see their own rows. Platform admins see all rows and may filter "
        "with `event_id` and `status`."
    ),
)
def list_registrations(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[RegistrationService, Depends(get_registration_service)],
    event_id: Annotated[int | None, Query(ge=1)] = None,
    registration_status: Annotated[
        RegistrationStatus | None,
        Query(alias="status", description="registered, waitlisted, or cancelled."),
    ] = None,
) -> list[RegistrationRead]:
    return service.list_registrations(
        actor,
        event_id=event_id,
        status=registration_status,
    )


@router.get("/{registration_id}", response_model=RegistrationRead, summary="Get one registration")
def get_registration(
    registration_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[RegistrationService, Depends(get_registration_service)],
) -> RegistrationRead:
    return service.get_registration(actor, registration_id)


@router.post(
    "",
    response_model=RegistrationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register for an event",
)
def register_for_event(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[RegistrationService, Depends(get_registration_service)],
    payload: Annotated[RegistrationCreate, Body(openapi_examples=_REGISTER_EXAMPLES)],
) -> RegistrationRead:
    return service.register(actor, payload)


@router.post(
    "/{registration_id}/cancel",
    response_model=RegistrationRead,
    summary="Cancel a registration",
    description=(
        "Attendees cancel their own row. Admins may cancel any row. "
        "Freeing a registered seat promotes the oldest waitlisted attendee."
    ),
)
def cancel_registration(
    registration_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[RegistrationService, Depends(get_registration_service)],
) -> RegistrationRead:
    return service.cancel(actor, registration_id)
