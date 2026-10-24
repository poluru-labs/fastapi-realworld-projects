from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_media_service
from app.schemas.media import PresetCreate, PresetRead, PresetUpdate
from app.schemas.user import UserRead
from app.services.media_service import MediaService

router = APIRouter()


@router.get(
    "",
    response_model=list[PresetRead],
    summary="List processing presets",
    description="Users see their presets. Platform admin sees all presets.",
)
def list_presets(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MediaService, Depends(get_media_service)],
) -> list[PresetRead]:
    return service.list_presets(current_user)


@router.post(
    "",
    response_model=PresetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a preset",
)
def create_preset(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MediaService, Depends(get_media_service)],
    payload: PresetCreate,
) -> PresetRead:
    return service.create_preset(current_user, payload)


@router.get(
    "/{preset_id}",
    response_model=PresetRead,
    summary="Get a preset",
)
def get_preset(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MediaService, Depends(get_media_service)],
    preset_id: int,
) -> PresetRead:
    return service.get_preset(current_user, preset_id)


@router.patch(
    "/{preset_id}",
    response_model=PresetRead,
    summary="Update a preset",
    description="Only the owner may edit.",
)
def update_preset(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MediaService, Depends(get_media_service)],
    preset_id: int,
    payload: PresetUpdate,
) -> PresetRead:
    return service.update_preset(current_user, preset_id, payload)


@router.delete(
    "/{preset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a preset",
)
def delete_preset(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[MediaService, Depends(get_media_service)],
    preset_id: int,
) -> None:
    service.delete_preset(current_user, preset_id)
