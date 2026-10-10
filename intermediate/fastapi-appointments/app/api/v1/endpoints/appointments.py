from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_appointment_service, get_current_user
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentStatus,
    AppointmentUpdate,
)
from app.schemas.user import UserRead
from app.services.appointment_service import AppointmentService

router = APIRouter()

_BOOK_EXAMPLES = {
    "checkup": {
        "summary": "30-minute visit",
        "description": "Overlap with another active booking on the same provider returns 409.",
        "value": {
            "provider_id": 1,
            "title": "Annual checkup",
            "notes": "First visit",
            "starts_at": "2026-12-10T10:00:00+00:00",
            "ends_at": "2026-12-10T10:30:00+00:00",
        },
    }
}


@router.get(
    "",
    response_model=list[AppointmentRead],
    summary="List appointments",
    description=(
        "Clients see their own rows. Platform admins see every row and may filter with user_id. "
        "Filter with status, provider_id, from_time, and to_time. Results sort by starts_at."
    ),
)
def list_appointments(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
    appointment_status: Annotated[
        AppointmentStatus | None,
        Query(alias="status", description="scheduled, confirmed, completed, or cancelled."),
    ] = None,
    provider_id: Annotated[int | None, Query(ge=1)] = None,
    user_id: Annotated[
        int | None,
        Query(ge=1, description="Platform admin only. Filter by client user id."),
    ] = None,
    from_time: Annotated[
        datetime | None,
        Query(description="Keep appointments that end at or after this instant (ISO-8601)."),
    ] = None,
    to_time: Annotated[
        datetime | None,
        Query(description="Keep appointments that start at or before this instant (ISO-8601)."),
    ] = None,
) -> list[AppointmentRead]:
    return service.list_appointments(
        actor,
        status=appointment_status,
        provider_id=provider_id,
        user_id=user_id,
        from_time=from_time,
        to_time=to_time,
    )


@router.post(
    "",
    response_model=AppointmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Book an appointment",
    description=(
        "Any signed-in user books for themselves. The provider must be active. "
        "Duration is 15 minutes to 8 hours. Cancelled slots do not block overlap."
    ),
    responses={
        409: {"description": "Inactive provider or overlapping time window."},
        422: {"description": "Invalid time window."},
    },
)
def book_appointment(
    payload: Annotated[AppointmentCreate, Body(openapi_examples=_BOOK_EXAMPLES)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> AppointmentRead:
    return service.book_appointment(actor, payload)


@router.get(
    "/{appointment_id}",
    response_model=AppointmentRead,
    summary="Get one appointment",
    description=(
        "Clients may read their own appointments. Admins may read any. "
        "Someone else's id returns 404, not 403."
    ),
    responses={404: {"description": "Unknown id, or not yours and you are not an admin."}},
)
def get_appointment(
    appointment_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> AppointmentRead:
    return service.get_appointment(actor, appointment_id)


@router.patch(
    "/{appointment_id}",
    response_model=AppointmentRead,
    summary="Reschedule or edit notes",
    description=(
        "Client or platform admin. Only while status is scheduled. "
        "Changing times runs the same overlap check as create."
    ),
    responses={
        403: {"description": "Not the client or an admin."},
        409: {"description": "Not scheduled, bad window, or overlap."},
    },
)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> AppointmentRead:
    return service.update_appointment(actor, appointment_id, payload)


@router.post(
    "/{appointment_id}/confirm",
    response_model=AppointmentRead,
    summary="Confirm a scheduled visit",
    description="Platform admin only. Move: scheduled → confirmed.",
    responses={409: {"description": "Wrong current status."}},
)
def confirm_appointment(
    appointment_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> AppointmentRead:
    return service.confirm_appointment(actor, appointment_id)


@router.post(
    "/{appointment_id}/complete",
    response_model=AppointmentRead,
    summary="Mark a visit complete",
    description="Platform admin only. Move: confirmed → completed.",
    responses={409: {"description": "Wrong current status."}},
)
def complete_appointment(
    appointment_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> AppointmentRead:
    return service.complete_appointment(actor, appointment_id)


@router.post(
    "/{appointment_id}/cancel",
    response_model=AppointmentRead,
    summary="Cancel a visit",
    description=(
        "Client or platform admin while status is scheduled or confirmed. "
        "Move to cancelled."
    ),
    responses={
        403: {"description": "Not the client or an admin."},
        409: {"description": "Already completed or cancelled."},
    },
)
def cancel_appointment(
    appointment_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> AppointmentRead:
    return service.cancel_appointment(actor, appointment_id)
