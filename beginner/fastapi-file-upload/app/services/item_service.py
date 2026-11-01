from app.core.exceptions import NotFoundError
from app.repositories.item_repository import ItemRepository
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate


class ItemService:
    def __init__(self, repository: ItemRepository) -> None:
        self._repo = repository

    def list_items(self) -> list[ItemRead]:
        return self._repo.list_all()

    def get_item(self, item_id: int) -> ItemRead:
        item = self._repo.get(item_id)
        if item is None:
            raise NotFoundError("Item", item_id)
        return item

    def create_item(self, payload: ItemCreate) -> ItemRead:
        return self._repo.create(payload)

    def replace_item(self, item_id: int, payload: ItemCreate) -> ItemRead:
        item = self._repo.replace(item_id, payload)
        if item is None:
            raise NotFoundError("Item", item_id)
        return item

    def update_item(self, item_id: int, payload: ItemUpdate) -> ItemRead:
        item = self._repo.update(item_id, payload)
        if item is None:
            raise NotFoundError("Item", item_id)
        return item

    def delete_item(self, item_id: int) -> ItemRead:
        item = self._repo.delete(item_id)
        if item is None:
            raise NotFoundError("Item", item_id)
        return item
