from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import (
    get_current_user,
    get_optional_user,
    get_plan_service,
    get_subscription_service,
)
from app.schemas.plan import PlanCreate, PlanRead, PlanStatus, PlanUpdate
from app.schemas.subscription import SubscriptionRead
from app.schemas.user import UserRead
from app.services.plan_service import PlanService
from app.services.subscription_service import SubscriptionService

router = APIRouter()

_CREATE_EXAMPLES = {
    "monthly": {
        "summary": "Monthly SaaS tier",
        "value": {
            "name": "Team Monthly",
            "summary": "For growing teams.",
            "description": "Unlimited projects and email support.",
            "price_cents": 4900,
            "interval": "monthly",
            "tags": ["team", "monthly"],
        },
    }
}


@router.get(
    "",
    response_model=list[PlanRead],
    summary="List plans",
    description=(
        "Anonymous callers see **active** plans only. "
        "Platform admins may pass `status` to include drafts or archived rows."
    ),
)
def list_plans(
    service: Annotated[PlanService, Depends(get_plan_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
    plan_status: Annotated[
        PlanStatus | None,
        Query(alias="status", description="Admin-only filter for draft, active, or archived."),
    ] = None,
    tag: Annotated[str | None, Query(description="Filter by tag on active plans.")] = None,
    query: Annotated[
        str | None,
        Query(description="Case-insensitive search in name or summary."),
    ] = None,
    interval: Annotated[
        str | None,
        Query(description="Filter by billing interval: monthly or yearly."),
    ] = None,
) -> list[PlanRead]:
    return service.list_plans(
        actor,
        status=plan_status,
        tag=tag,
        query=query,
        interval=interval,
    )


@router.get(
    "/{slug}",
    response_model=PlanRead,
    summary="Get one plan",
    description="Active plans are public. Draft and archived plans return **404** for non-admins.",
)
def get_plan(
    slug: str,
    service: Annotated[PlanService, Depends(get_plan_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)],
) -> PlanRead:
    return service.get_plan(actor, slug)


@router.post(
    "",
    response_model=PlanRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft plan (admin)",
)
def create_plan(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PlanService, Depends(get_plan_service)],
    payload: Annotated[PlanCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> PlanRead:
    return service.create_plan(actor, payload)


@router.patch(
    "/{slug}",
    response_model=PlanRead,
    summary="Update a draft plan (admin)",
)
def update_plan(
    slug: str,
    payload: PlanUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PlanService, Depends(get_plan_service)],
) -> PlanRead:
    return service.update_plan(actor, slug, payload)


@router.post("/{slug}/activate", response_model=PlanRead, summary="Activate a draft plan (admin)")
def activate_plan(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PlanService, Depends(get_plan_service)],
) -> PlanRead:
    return service.transition(actor, slug, PlanStatus.ACTIVE)


@router.post(
    "/{slug}/deactivate",
    response_model=PlanRead,
    summary="Return an active plan to draft (admin)",
    description="Blocked with **409** while active subscriptions exist.",
)
def deactivate_plan(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PlanService, Depends(get_plan_service)],
) -> PlanRead:
    return service.transition(actor, slug, PlanStatus.DRAFT)


@router.post("/{slug}/archive", response_model=PlanRead, summary="Archive a plan (admin)")
def archive_plan(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PlanService, Depends(get_plan_service)],
) -> PlanRead:
    return service.transition(actor, slug, PlanStatus.ARCHIVED)


@router.post(
    "/{slug}/restore",
    response_model=PlanRead,
    summary="Restore an archived plan to draft (admin)",
)
def restore_plan(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[PlanService, Depends(get_plan_service)],
) -> PlanRead:
    return service.transition(actor, slug, PlanStatus.DRAFT)


@router.get(
    "/{slug}/subscriptions",
    response_model=list[SubscriptionRead],
    summary="List subscribers for a plan (admin)",
)
def list_plan_subscriptions(
    slug: str,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> list[SubscriptionRead]:
    return service.list_for_plan_slug(actor, slug)
