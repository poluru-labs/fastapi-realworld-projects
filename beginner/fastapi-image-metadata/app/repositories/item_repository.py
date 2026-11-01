from app.schemas.item import ItemCreate, ItemRead, ItemUpdate

_MOCK_ITEMS: dict[int, ItemRead] = {
    1: ItemRead(id=1, name="Widget A", price=9.99, in_stock=True),
    2: ItemRead(id=2, name="Widget B", price=19.99, in_stock=True),
    3: ItemRead(id=3, name="Widget C", price=4.50, in_stock=False),
}


class ItemRepository:
    def __init__(self) -> None:
        self._items = dict(_MOCK_ITEMS)
        self._next_id = max(self._items.keys(), default=0) + 1

    def list_all(self) -> list[ItemRead]:
        return list(self._items.values())

    def get(self, item_id: int) -> ItemRead | None:
        return self._items.get(item_id)

    def create(self, payload: ItemCreate) -> ItemRead:
        item = ItemRead(id=self._next_id, **payload.model_dump())
        self._items[self._next_id] = item
        self._next_id += 1
        return item

    def replace(self, item_id: int, payload: ItemCreate) -> ItemRead | None:
        if item_id not in self._items:
            return None
        item = ItemRead(id=item_id, **payload.model_dump())
        self._items[item_id] = item
        return item

    def update(self, item_id: int, payload: ItemUpdate) -> ItemRead | None:
        existing = self._items.get(item_id)
        if existing is None:
            return None
        data = existing.model_dump()
        data.update(payload.model_dump(exclude_unset=True))
        item = ItemRead(**data)
        self._items[item_id] = item
        return item

    def delete(self, item_id: int) -> ItemRead | None:
        return self._items.pop(item_id, None)
