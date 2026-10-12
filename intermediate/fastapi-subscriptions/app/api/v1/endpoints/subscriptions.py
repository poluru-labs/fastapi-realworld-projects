from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_current_user, get_subscription_service
from app.schemas.subscription import SubscriptionCreate, SubscriptionRead, SubscriptionStatus
from app.schemas.user import UserRead
from app.services.subscription_service import SubscriptionService

router = APIRouter()

_SUBSCRIBE_EXAMPLES = {
    "starter": {
        "summary": "Subscribe to a public plan",
        "description": (
            "Starts a billing period based on the plan interval (30 or 365 days). "
            "Duplicate active subscriptions for the same plan return **409**."
        ),
        "value": {"plan_slug": "starter-monthly"},
    }
}


@router.get(
    "",
    response_model=list[SubscriptionRead],
    summary="List subscriptions",
    description=(
        "Signed-in users see their own rows. Platform admins see all rows and may filter "
        "with `plan_id` and `status`."
    ),
)
def list_subscriptions(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
    plan_id: Annotated[int | None, Query(ge=1)] = None,
    subscription_status: Annotated[
        SubscriptionStatus | None,
        Query(alias="status", description="active or cancelled."),
    ] = None,
) -> list[SubscriptionRead]:
    return service.list_subscriptions(
        actor,
        plan_id=plan_id,
        status=subscription_status,
    )


@router.get("/{subscription_id}", response_model=SubscriptionRead, summary="Get one subscription")
def get_subscription(
    subscription_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionRead:
    return service.get_subscription(actor, subscription_id)


@router.post(
    "",
    response_model=SubscriptionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to a plan",
)
def subscribe(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
    payload: Annotated[SubscriptionCreate, Body(openapi_examples=_SUBSCRIBE_EXAMPLES)],
) -> SubscriptionRead:
    return service.subscribe(actor, payload)


@router.post(
    "/{subscription_id}/cancel",
    response_model=SubscriptionRead,
    summary="Cancel a subscription",
    description="Subscribers cancel their own row. Admins may cancel any active subscription.",
)
def cancel_subscription(
    subscription_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionRead:
    return service.cancel(actor, subscription_id)
