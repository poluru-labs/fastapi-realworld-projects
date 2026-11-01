from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_source_service
from app.schemas.source import SourceCreate, SourceRead, SourceUpdate
from app.schemas.user import UserRead
from app.services.source_service import SourceService

router = APIRouter()


@router.get(
    "",
    response_model=list[SourceRead],
    summary="List upstream sources",
    description=(
        "Returns sources you own. Platform admins see every registered mock upstream."
    ),
)
def list_sources(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> list[SourceRead]:
    return service.list_sources(current_user)


@router.post(
    "",
    response_model=SourceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a mock upstream",
    description=(
        "Each source points at a `mock_catalog` (`users`, `orders`, `inventory`). "
        "The `base_url` is documentation-only in this sample; responses come from the catalog."
    ),
    responses={409: {"description": "Slug already taken."}},
)
def create_source(
    payload: SourceCreate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> SourceRead:
    return service.create_source(payload, current_user)


@router.get(
    "/{slug}",
    response_model=SourceRead,
    summary="Read one source",
    responses={404: {"description": "Missing or not visible to the caller."}},
)
def get_source(
    slug: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> SourceRead:
    return service.get_source(slug, current_user)


@router.patch(
    "/{slug}",
    response_model=SourceRead,
    summary="Update source metadata",
    description=(
        "Pause a source with `is_active: false` so aggregate fragments return 409 while paused."
    ),
)
def update_source(
    slug: str,
    payload: SourceUpdate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> SourceRead:
    return service.update_source(slug, payload, current_user)


@router.delete(
    "/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a source",
)
def delete_source(
    slug: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> None:
    service.delete_source(slug, current_user)
