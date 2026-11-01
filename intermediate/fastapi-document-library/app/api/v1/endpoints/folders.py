from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_folder_service, get_optional_user
from app.schemas.folder import FolderCreate, FolderRead, FolderUpdate
from app.schemas.user import UserRead
from app.services.folder_service import FolderService

router = APIRouter()


@router.get(
    "",
    response_model=list[FolderRead],
    summary="List your folders",
    description="Platform admins see every folder. Authors only see folders they own.",
)
def list_folders(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[FolderService, Depends(get_folder_service)],
) -> list[FolderRead]:
    return service.list_folders(current_user)


@router.post(
    "",
    response_model=FolderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a folder",
    responses={409: {"description": "Slug already taken or could not be derived."}},
)
def create_folder(
    payload: FolderCreate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[FolderService, Depends(get_folder_service)],
) -> FolderRead:
    return service.create_folder(current_user, payload)


@router.get(
    "/{folder_slug}",
    response_model=FolderRead,
    summary="Read folder metadata",
    description=(
        "Owners and admins always see the folder. Other callers only see folders "
        "that contain at least one published document."
    ),
)
def get_folder(
    folder_slug: str,
    service: Annotated[FolderService, Depends(get_folder_service)],
    actor: Annotated[UserRead | None, Depends(get_optional_user)] = None,
) -> FolderRead:
    return service.get_folder(actor, folder_slug)


@router.patch(
    "/{folder_slug}",
    response_model=FolderRead,
    summary="Update folder metadata",
)
def update_folder(
    folder_slug: str,
    payload: FolderUpdate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[FolderService, Depends(get_folder_service)],
) -> FolderRead:
    return service.update_folder(current_user, folder_slug, payload)


@router.delete(
    "/{folder_slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a folder and its documents",
)
def delete_folder(
    folder_slug: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[FolderService, Depends(get_folder_service)],
) -> None:
    service.delete_folder(current_user, folder_slug)
