from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CustomerAuth, get_usage_service
from app.schemas.usage import UsageEventCreate, UsageEventRead, UsageSummaryRead
from app.services.usage_service import UsageService

router = APIRouter()


@router.post(
    "/events",
    response_model=UsageEventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest usage event",
    description=(
        "Customer credential (`X-Api-Key`). "
        "Each `(customer, idempotency_key)` pair is stored once. "
        "Replays return the original event with HTTP 201. "
        "The `request_id` field mirrors `X-Request-ID` when you send one."
    ),
    responses={
        401: {"description": "Missing or invalid X-Api-Key"},
        404: {"description": "Unknown meter_code"},
    },
)
async def ingest_usage_event(
    payload: UsageEventCreate,
    customer: CustomerAuth,
    service: Annotated[UsageService, Depends(get_usage_service)],
) -> UsageEventRead:
    return await service.ingest_event(customer.id, payload)


@router.get(
    "/summary",
    response_model=UsageSummaryRead,
    summary="Usage totals for current period",
    description=(
        "Customer credential. Sums `quantity` by meter between the active subscription "
        "`current_period_start` (inclusive) and `current_period_end` (exclusive)."
    ),
)
async def usage_summary(
    customer: CustomerAuth,
    service: Annotated[UsageService, Depends(get_usage_service)],
) -> UsageSummaryRead:
    return await service.usage_summary(customer.id)
