from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_appointment_service, get_current_user
from app.schemas.provider import ProviderCreate, ProviderRead, ProviderUpdate
from app.schemas.user import UserRead
from app.services.appointment_service import AppointmentService

router = APIRouter()

_CREATE_EXAMPLES = {
    "gp": {
        "summary": "New clinician",
        "value": {"name": "Dr Sam Rivera", "specialty": "Evening clinic"},
    }
}


@router.get(
    "",
    response_model=list[ProviderRead],
    summary="List providers",
    description=(
        "Any signed-in user. Inactive providers are hidden unless you are a platform admin "
        "and pass include_inactive=true."
    ),
)
def list_providers(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
    include_inactive: Annotated[bool, Query(description="Platform admin only.")] = False,
) -> list[ProviderRead]:
    return service.list_providers(actor, include_inactive=include_inactive)


@router.post(
    "",
    response_model=ProviderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a provider",
    description="Platform admin only.",
    responses={403: {"description": "Not a platform admin."}},
)
def create_provider(
    payload: Annotated[ProviderCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> ProviderRead:
    return service.create_provider(actor, payload)


@router.get(
    "/{provider_id}",
    response_model=ProviderRead,
    summary="Get one provider",
    responses={404: {"description": "Unknown provider, or inactive and you are not an admin."}},
)
def get_provider(
    provider_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> ProviderRead:
    return service.get_provider(actor, provider_id)


@router.patch(
    "/{provider_id}",
    response_model=ProviderRead,
    summary="Update a provider",
    description="Platform admin only. Omitted fields stay as they are.",
)
def update_provider(
    provider_id: int,
    payload: ProviderUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> ProviderRead:
    return service.update_provider(actor, provider_id, payload)


@router.post(
    "/{provider_id}/deactivate",
    response_model=ProviderRead,
    summary="Deactivate a provider",
    description="Platform admin only. New bookings against this provider return 409.",
)
def deactivate_provider(
    provider_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> ProviderRead:
    return service.deactivate_provider(actor, provider_id)


@router.post(
    "/{provider_id}/activate",
    response_model=ProviderRead,
    summary="Activate a provider",
    description="Platform admin only.",
)
def activate_provider(
    provider_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
) -> ProviderRead:
    return service.activate_provider(actor, provider_id)
