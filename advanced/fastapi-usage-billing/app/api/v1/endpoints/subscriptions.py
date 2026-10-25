from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import AdminAuth, get_subscription_service
from app.schemas.subscription import SubscriptionCreate, SubscriptionRead
from app.services.subscription_service import SubscriptionService

router = APIRouter()


@router.post(
    "",
    response_model=SubscriptionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start subscription",
    description=(
        "Attach a plan to a customer. One active subscription per customer. "
        "The billing period starts now and runs 30 days for usage aggregation."
    ),
    responses={
        404: {"description": "Customer or plan not found"},
        409: {"description": "Customer already subscribed"},
    },
)
async def create_subscription(
    customer_id: int,
    payload: SubscriptionCreate,
    _admin: AdminAuth,
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionRead:
    return await service.create_subscription(customer_id, payload)


@router.get(
    "",
    response_model=SubscriptionRead,
    summary="Active subscription",
    responses={404: {"description": "No active subscription"}},
)
async def get_active_subscription(
    customer_id: int,
    _admin: AdminAuth,
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionRead:
    return await service.get_active(customer_id)
