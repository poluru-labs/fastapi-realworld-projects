from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_delivery_service
from app.schemas.user import UserRead
from app.schemas.webhook import DeliveryRead, DeliveryStatus
from app.services.delivery_service import DeliveryService

router = APIRouter()


@router.get(
    "",
    response_model=list[DeliveryRead],
    summary="List inbox deliveries",
    description="Filter by `endpoint_slug` and `status`. Newest first.",
)
def list_deliveries(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[DeliveryService, Depends(get_delivery_service)],
    endpoint_slug: Annotated[str | None, Query(max_length=64)] = None,
    delivery_status: Annotated[
        DeliveryStatus | None,
        Query(alias="status", description="pending or acked"),
    ] = None,
) -> list[DeliveryRead]:
    return service.list_deliveries(
        current_user,
        endpoint_slug=endpoint_slug,
        status=delivery_status,
    )


@router.get(
    "/{delivery_id}",
    response_model=DeliveryRead,
    summary="Get one delivery",
)
def get_delivery(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[DeliveryService, Depends(get_delivery_service)],
    delivery_id: int,
) -> DeliveryRead:
    return service.get_delivery(current_user, delivery_id)


@router.post(
    "/{delivery_id}/ack",
    response_model=DeliveryRead,
    summary="Acknowledge a delivery",
    responses={409: {"description": "Already acknowledged."}},
)
def ack_delivery(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[DeliveryService, Depends(get_delivery_service)],
    delivery_id: int,
) -> DeliveryRead:
    return service.ack(current_user, delivery_id)
