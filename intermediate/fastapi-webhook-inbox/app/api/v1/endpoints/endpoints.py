from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.api.deps import get_current_user, get_delivery_service, get_endpoint_service
from app.schemas.user import UserRead
from app.schemas.webhook import (
    SLUG_PATTERN,
    DeliveryRead,
    EndpointCreate,
    EndpointProvisioned,
    EndpointRead,
    EndpointUpdate,
)
from app.services.delivery_service import DeliveryService
from app.services.endpoint_service import EndpointService

router = APIRouter()

EndpointSlug = Annotated[
    str,
    Path(pattern=SLUG_PATTERN.pattern, min_length=2, max_length=64),
]


@router.get(
    "",
    response_model=list[EndpointRead],
    summary="List webhook endpoints",
    description="Users see their endpoints. Platform admin sees all.",
)
def list_endpoints(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EndpointService, Depends(get_endpoint_service)],
) -> list[EndpointRead]:
    return service.list_endpoints(current_user)


@router.post(
    "",
    response_model=EndpointProvisioned,
    status_code=status.HTTP_201_CREATED,
    summary="Provision an endpoint",
    description="Returns a one-time **webhook_token** for `X-Webhook-Token` on ingest.",
)
def provision_endpoint(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EndpointService, Depends(get_endpoint_service)],
    payload: EndpointCreate,
) -> EndpointProvisioned:
    return service.provision(current_user, payload)


@router.get(
    "/{slug}/deliveries",
    response_model=list[DeliveryRead],
    summary="Inbox for one endpoint",
)
def list_endpoint_deliveries(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[DeliveryService, Depends(get_delivery_service)],
    slug: EndpointSlug,
) -> list[DeliveryRead]:
    return service.list_for_endpoint(current_user, slug)


@router.get(
    "/{slug}",
    response_model=EndpointRead,
    summary="Get endpoint metadata",
    description="Returns **404** when missing or owned by another user.",
)
def get_endpoint(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EndpointService, Depends(get_endpoint_service)],
    slug: EndpointSlug,
) -> EndpointRead:
    return service.get_endpoint(current_user, slug)


@router.patch(
    "/{slug}",
    response_model=EndpointRead,
    summary="Update an endpoint",
    description="Only the owner may edit. Use `status: paused` to stop ingest.",
)
def update_endpoint(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EndpointService, Depends(get_endpoint_service)],
    slug: EndpointSlug,
    payload: EndpointUpdate,
) -> EndpointRead:
    return service.update_endpoint(current_user, slug, payload)


@router.delete(
    "/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an endpoint",
    description="Removes the endpoint and its delivery inbox.",
)
def delete_endpoint(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[EndpointService, Depends(get_endpoint_service)],
    slug: EndpointSlug,
) -> None:
    service.delete_endpoint(current_user, slug)
