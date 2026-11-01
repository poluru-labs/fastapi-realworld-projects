from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, get_flag_service
from app.schemas.flag import FlagCreate, FlagEnvironment, FlagRead, FlagUpdate
from app.schemas.user import UserRead
from app.services.flag_service import FlagService

router = APIRouter()


@router.get(
    "",
    response_model=list[FlagRead],
    summary="List feature flags",
    description="Owners see their flags. Platform admins see every flag.",
)
def list_flags(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[FlagService, Depends(get_flag_service)],
    environment: Annotated[FlagEnvironment | None, Query()] = None,
) -> list[FlagRead]:
    return service.list_flags(
        current_user,
        environment=environment.value if environment else None,
    )


@router.post(
    "",
    response_model=FlagRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a feature flag",
    responses={409: {"description": "Flag key already exists."}},
)
def create_flag(
    payload: FlagCreate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[FlagService, Depends(get_flag_service)],
) -> FlagRead:
    return service.create_flag(current_user, payload)


@router.get(
    "/{key}",
    response_model=FlagRead,
    summary="Read one flag",
)
def get_flag(
    key: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[FlagService, Depends(get_flag_service)],
) -> FlagRead:
    return service.get_flag(current_user, key)


@router.patch(
    "/{key}",
    response_model=FlagRead,
    summary="Update flag targeting",
)
def update_flag(
    key: str,
    payload: FlagUpdate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[FlagService, Depends(get_flag_service)],
) -> FlagRead:
    return service.update_flag(current_user, key, payload)


@router.delete(
    "/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a flag",
)
def delete_flag(
    key: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[FlagService, Depends(get_flag_service)],
) -> None:
    service.delete_flag(current_user, key)
