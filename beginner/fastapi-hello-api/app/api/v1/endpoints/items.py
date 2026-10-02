from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_item_service
from app.schemas.item import ItemCreate, ItemDeleteResponse, ItemRead, ItemUpdate
from app.services.item_service import ItemService

router = APIRouter()


@router.get("", response_model=list[ItemRead])
def list_items(service: Annotated[ItemService, Depends(get_item_service)]) -> list[ItemRead]:
    return service.list_items()


@router.get("/{item_id}", response_model=ItemRead)
def get_item(
    item_id: int,
    service: Annotated[ItemService, Depends(get_item_service)],
) -> ItemRead:
    return service.get_item(item_id)


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    service: Annotated[ItemService, Depends(get_item_service)],
) -> ItemRead:
    return service.create_item(payload)


@router.put("/{item_id}", response_model=ItemRead)
def replace_item(
    item_id: int,
    payload: ItemCreate,
    service: Annotated[ItemService, Depends(get_item_service)],
) -> ItemRead:
    return service.replace_item(item_id, payload)


@router.patch("/{item_id}", response_model=ItemRead)
def update_item(
    item_id: int,
    payload: ItemUpdate,
    service: Annotated[ItemService, Depends(get_item_service)],
) -> ItemRead:
    return service.update_item(item_id, payload)


@router.delete("/{item_id}", response_model=ItemDeleteResponse)
def delete_item(
    item_id: int,
    service: Annotated[ItemService, Depends(get_item_service)],
) -> ItemDeleteResponse:
    removed = service.delete_item(item_id)
    return ItemDeleteResponse(item=removed)
