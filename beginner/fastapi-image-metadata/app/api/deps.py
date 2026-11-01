from functools import lru_cache

from app.repositories.item_repository import ItemRepository
from app.services.item_service import ItemService


@lru_cache
def get_item_repository() -> ItemRepository:
    return ItemRepository()


def get_item_service() -> ItemService:
    return ItemService(get_item_repository())
