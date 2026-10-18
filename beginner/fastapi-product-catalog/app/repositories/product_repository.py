from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache

from app.core.exceptions import ConflictError, NotFoundError


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _sku_key(sku: str) -> str:
    return sku.strip().upper()


@dataclass
class ProductRecord:
    id: int
    sku: str
    name: str
    description: str = ""
    price: float = 0.0
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    stock_quantity: int = 0
    featured: bool = False
    discontinued: bool = False
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


class ProductRepository:
    def __init__(self) -> None:
        now = _utcnow()
        self._records: dict[int, ProductRecord] = {
            1: ProductRecord(
                id=1,
                sku="HUB-USBC-7IN1",
                name="USB-C 7-in-1 Hub",
                description="HDMI, USB-A, and SD card ports for laptops.",
                price=49.99,
                category="accessories",
                tags=["usb-c", "hub", "travel"],
                stock_quantity=24,
                featured=True,
                created_at=now,
                updated_at=now,
            ),
            2: ProductRecord(
                id=2,
                sku="MOUSE-WIRELESS-MX",
                name="Wireless Mouse MX",
                description="Ergonomic mouse with silent clicks.",
                price=29.5,
                category="peripherals",
                tags=["mouse", "wireless"],
                stock_quantity=120,
                created_at=now,
                updated_at=now,
            ),
            3: ProductRecord(
                id=3,
                sku="KB-MECH-87",
                name="Mechanical Keyboard 87-key",
                description="Hot-swappable switches; layout TKL.",
                price=89.0,
                category="peripherals",
                tags=["keyboard", "mechanical"],
                stock_quantity=0,
                discontinued=True,
                created_at=now,
                updated_at=now,
            ),
        }
        self._next_id = 4
        self._sku_index: dict[str, int] = {
            _sku_key(r.sku): r.id for r in self._records.values()
        }

    def _touch(self, record: ProductRecord) -> None:
        record.updated_at = _utcnow()

    def list_categories(self) -> list[str]:
        cats = {r.category.strip().lower() for r in self._records.values() if not r.discontinued}
        return sorted(cats)

    def list_products(
        self,
        *,
        category: str | None = None,
        search: str | None = None,
        in_stock: bool | None = None,
        featured: bool | None = None,
        discontinued: bool = False,
    ) -> list[ProductRecord]:
        rows = [r for r in self._records.values() if r.discontinued == discontinued]
        if category is not None:
            needle = category.strip().lower()
            rows = [r for r in rows if r.category.strip().lower() == needle]
        if featured is not None:
            rows = [r for r in rows if r.featured == featured]
        if in_stock is not None:
            rows = [r for r in rows if (r.stock_quantity > 0) == in_stock]
        if search:
            q = search.strip().lower()
            rows = [
                r
                for r in rows
                if q in r.name.lower()
                or q in r.sku.lower()
                or q in r.description.lower()
                or q in r.category.lower()
                or any(q in t for t in r.tags)
            ]
        rows.sort(key=lambda r: (-int(r.featured), r.name.lower()))
        return rows

    def get(self, product_id: int) -> ProductRecord:
        record = self._records.get(product_id)
        if record is None:
            raise NotFoundError("Product", product_id)
        return record

    def get_by_sku(self, sku: str) -> ProductRecord:
        product_id = self._sku_index.get(_sku_key(sku))
        if product_id is None:
            raise NotFoundError("Product", sku)
        return self.get(product_id)

    def create(
        self,
        *,
        sku: str,
        name: str,
        description: str,
        price: float,
        category: str,
        tags: list[str],
        stock_quantity: int,
        featured: bool,
    ) -> ProductRecord:
        key = _sku_key(sku)
        if key in self._sku_index:
            raise ConflictError("A product with this SKU already exists.")
        record = ProductRecord(
            id=self._next_id,
            sku=key,
            name=name,
            description=description,
            price=price,
            category=category.strip().lower(),
            tags=tags,
            stock_quantity=stock_quantity,
            featured=featured,
        )
        self._next_id += 1
        self._records[record.id] = record
        self._sku_index[key] = record.id
        return record

    def update(
        self,
        product_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        price: float | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        stock_quantity: int | None = None,
        featured: bool | None = None,
    ) -> ProductRecord:
        record = self.get(product_id)
        if name is not None:
            record.name = name
        if description is not None:
            record.description = description
        if price is not None:
            record.price = price
        if category is not None:
            record.category = category.strip().lower()
        if tags is not None:
            record.tags = tags
        if stock_quantity is not None:
            record.stock_quantity = stock_quantity
        if featured is not None:
            record.featured = featured
        self._touch(record)
        return record

    def set_featured(self, product_id: int, *, featured: bool) -> ProductRecord:
        record = self.get(product_id)
        record.featured = featured
        self._touch(record)
        return record

    def set_discontinued(self, product_id: int, *, discontinued: bool) -> ProductRecord:
        record = self.get(product_id)
        record.discontinued = discontinued
        self._touch(record)
        return record

    def delete(self, product_id: int) -> None:
        record = self.get(product_id)
        self._sku_index.pop(_sku_key(record.sku), None)
        del self._records[product_id]


@lru_cache
def get_product_repository() -> ProductRepository:
    return ProductRepository()
