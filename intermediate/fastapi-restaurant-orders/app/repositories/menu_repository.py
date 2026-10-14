from dataclasses import dataclass, field
from datetime import datetime

from app.schemas.menu import MenuItemStatus


@dataclass
class MenuItemRecord:
    id: int
    slug: str
    name: str
    description: str
    price_cents: int
    category: str
    status: MenuItemStatus
    available: bool
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


def _seed_menu() -> dict[int, MenuItemRecord]:
    return {
        1: MenuItemRecord(
            id=1,
            slug="classic-burger",
            name="Classic Burger",
            description="Beef patty, lettuce, tomato.",
            price_cents=1299,
            category="Mains",
            status=MenuItemStatus.ACTIVE,
            available=True,
            created_at=datetime.fromisoformat("2026-09-01T10:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-09-01T10:00:00+00:00"),
        ),
        2: MenuItemRecord(
            id=2,
            slug="fries",
            name="Crispy Fries",
            description="Salted shoestring fries.",
            price_cents=499,
            category="Sides",
            status=MenuItemStatus.ACTIVE,
            available=True,
            created_at=datetime.fromisoformat("2026-09-01T10:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-09-01T10:00:00+00:00"),
        ),
        3: MenuItemRecord(
            id=3,
            slug="draft-seasonal-soup",
            name="Draft seasonal soup",
            description="Not on the public menu yet.",
            price_cents=699,
            category="Mains",
            status=MenuItemStatus.DRAFT,
            available=True,
            created_at=datetime.fromisoformat("2026-09-02T10:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-09-02T10:00:00+00:00"),
        ),
    }


class MenuRepository:
    def __init__(self) -> None:
        self._items = dict(_seed_menu())
        self._by_slug = {item.slug: item for item in self._items.values()}
        self._next_id = max(self._items.keys(), default=0) + 1

    def list_all(self) -> list[MenuItemRecord]:
        return list(self._items.values())

    def get(self, item_id: int) -> MenuItemRecord | None:
        return self._items.get(item_id)

    def get_by_slug(self, slug: str) -> MenuItemRecord | None:
        return self._by_slug.get(slug)

    def slug_taken(self, slug: str, *, except_id: int | None = None) -> bool:
        existing = self._by_slug.get(slug)
        if existing is None:
            return False
        if except_id is not None and existing.id == except_id:
            return False
        return True

    def add(self, record: MenuItemRecord) -> MenuItemRecord:
        self._items[record.id] = record
        self._by_slug[record.slug] = record
        return record

    def save(self, record: MenuItemRecord) -> None:
        previous = self._items.get(record.id)
        if previous is not None and previous.slug != record.slug:
            self._by_slug.pop(previous.slug, None)
        self._items[record.id] = record
        self._by_slug[record.slug] = record

    def allocate_id(self) -> int:
        item_id = self._next_id
        self._next_id += 1
        return item_id

    def list_categories(self) -> list[str]:
        categories = {item.category for item in self._items.values()}
        return sorted(categories, key=str.casefold)
