from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_aggregate_service, get_current_user, get_optional_idempotency_key
from app.schemas.aggregate import AggregateCreate, AggregateRead, AggregateRunRead, AggregateUpdate
from app.schemas.user import UserRead
from app.services.aggregate_service import AggregateService

router = APIRouter()


@router.get(
    "",
    response_model=list[AggregateRead],
    summary="List aggregate plans",
)
def list_aggregates(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AggregateService, Depends(get_aggregate_service)],
) -> list[AggregateRead]:
    return service.list_aggregates(current_user)


@router.post(
    "",
    response_model=AggregateRead,
    status_code=status.HTTP_201_CREATED,
    summary="Define an aggregate plan",
    description=(
        "Plans start in `draft`. Each step names a fragment `key`, a `source_slug` you own, "
        "and a mock upstream `path` (for example `/v1/profile`)."
    ),
    responses={409: {"description": "Slug taken or duplicate fragment keys."}},
)
def create_aggregate(
    payload: AggregateCreate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AggregateService, Depends(get_aggregate_service)],
) -> AggregateRead:
    return service.create_aggregate(payload, current_user)


@router.get(
    "/{slug}",
    response_model=AggregateRead,
    summary="Read one aggregate plan",
)
def get_aggregate(
    slug: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AggregateService, Depends(get_aggregate_service)],
) -> AggregateRead:
    return service.get_aggregate(slug, current_user)


@router.patch(
    "/{slug}",
    response_model=AggregateRead,
    summary="Update a draft or published plan",
)
def update_aggregate(
    slug: str,
    payload: AggregateUpdate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AggregateService, Depends(get_aggregate_service)],
) -> AggregateRead:
    return service.update_aggregate(slug, payload, current_user)


@router.post(
    "/{slug}/publish",
    response_model=AggregateRead,
    summary="Publish an aggregate",
    description="Published plans can be executed. Draft plans return **409** on run.",
    responses={409: {"description": "Already published."}},
)
def publish_aggregate(
    slug: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AggregateService, Depends(get_aggregate_service)],
) -> AggregateRead:
    return service.publish_aggregate(slug, current_user)


@router.delete(
    "/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an aggregate plan",
)
def delete_aggregate(
    slug: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AggregateService, Depends(get_aggregate_service)],
) -> None:
    service.delete_aggregate(slug, current_user)


@router.post(
    "/{slug}/runs",
    response_model=AggregateRunRead,
    status_code=status.HTTP_201_CREATED,
    summary="Execute an aggregate",
    description=(
        "Fans out each fragment with `asyncio.gather` against the mock upstream client. "
        "Optional `Idempotency-Key` replays the same stored run for this user and slug."
    ),
    responses={
        409: {"description": "Plan is still draft or a source fragment is paused."},
    },
)
async def run_aggregate(
    slug: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AggregateService, Depends(get_aggregate_service)],
    idempotency_key: Annotated[str | None, Depends(get_optional_idempotency_key)] = None,
) -> AggregateRunRead:
    return await service.run_aggregate(slug, current_user, idempotency_key=idempotency_key)


@router.get(
    "/{slug}/runs",
    response_model=list[AggregateRunRead],
    summary="List previous runs",
)
def list_runs(
    slug: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[AggregateService, Depends(get_aggregate_service)],
) -> list[AggregateRunRead]:
    return service.list_runs(slug, current_user)
