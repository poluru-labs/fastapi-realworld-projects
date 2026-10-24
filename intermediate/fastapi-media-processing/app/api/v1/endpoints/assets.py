from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_media_service
from app.schemas.media import AssetCreate, AssetRead, AssetUpdate
from app.schemas.user import UserRead
from app.services.media_service import MediaService

router = APIRouter()


@router.get(
    "",
    response_model=list[AssetRead],
    summary="List media assets",
    description="Users see their uploads. Platform admin sees every asset.",
)
def list_assets(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MediaService, Depends(get_media_service)],
) -> list[AssetRead]:
    return service.list_assets(current_user)


@router.post(
    "",
    response_model=AssetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register an asset",
    description=(
        "Metadata-only registration (no binary upload in this sample). "
        "Use realistic mime types and dimensions for processing rules."
    ),
)
def create_asset(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MediaService, Depends(get_media_service)],
    payload: AssetCreate,
) -> AssetRead:
    return service.create_asset(current_user, payload)


@router.get(
    "/{asset_id}",
    response_model=AssetRead,
    summary="Get an asset",
    description="Returns **404** when the asset is missing or owned by another user.",
)
def get_asset(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MediaService, Depends(get_media_service)],
    asset_id: int,
) -> AssetRead:
    return service.get_asset(current_user, asset_id)


@router.patch(
    "/{asset_id}",
    response_model=AssetRead,
    summary="Rename an asset",
    description="Only the owner may edit. Admins can read but not patch others' assets.",
)
def update_asset(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MediaService, Depends(get_media_service)],
    asset_id: int,
    payload: AssetUpdate,
) -> AssetRead:
    return service.update_asset(current_user, asset_id, payload)


@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an asset",
)
def delete_asset(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MediaService, Depends(get_media_service)],
    asset_id: int,
) -> None:
    service.delete_asset(current_user, asset_id)
