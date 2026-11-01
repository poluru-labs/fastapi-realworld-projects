from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_api_key_service, get_current_user
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyRead, ApiKeyUpdate
from app.schemas.user import UserRead
from app.services.api_key_service import ApiKeyService

router = APIRouter()


@router.get(
    "",
    response_model=list[ApiKeyRead],
    summary="List API keys",
    description="Metadata only — secrets are never returned. Admins see every key.",
)
def list_keys(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
) -> list[ApiKeyRead]:
    return service.list_keys(current_user)


@router.post(
    "",
    response_model=ApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Create an API key",
    description="The full secret is returned once in `secret`. Store it securely.",
)
def create_key(
    payload: ApiKeyCreate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
) -> ApiKeyCreated:
    return service.create_key(current_user, payload)


@router.get(
    "/{key_id}",
    response_model=ApiKeyRead,
    summary="Read API key metadata",
)
def get_key(
    key_id: int,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
) -> ApiKeyRead:
    return service.get_key(current_user, key_id)


@router.patch(
    "/{key_id}",
    response_model=ApiKeyRead,
    summary="Rename or rescope a key",
    responses={409: {"description": "Key is revoked."}},
)
def update_key(
    key_id: int,
    payload: ApiKeyUpdate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
) -> ApiKeyRead:
    return service.update_key(current_user, key_id, payload)


@router.post(
    "/{key_id}/revoke",
    response_model=ApiKeyRead,
    summary="Revoke an API key",
)
def revoke_key(
    key_id: int,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
) -> ApiKeyRead:
    return service.revoke_key(current_user, key_id)


@router.post(
    "/{key_id}/rotate",
    response_model=ApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Rotate an API key",
    description="Revokes the old key and mints a new secret with the same scopes.",
)
def rotate_key(
    key_id: int,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
) -> ApiKeyCreated:
    return service.rotate_key(current_user, key_id)
