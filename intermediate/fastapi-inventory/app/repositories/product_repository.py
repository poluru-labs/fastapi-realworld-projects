from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProductRecord:
    id: int
    sku: str
    name: str
    description: str
    quantity_on_hand: int
    reorder_level: int
    is_active: bool
    updated_at: datetime


def _seed_products() -> dict[int, ProductRecord]:
    ts = datetime.fromisoformat("2026-03-01T12:00:00+00:00")
    return {
        1: ProductRecord(
            id=1,
            sku="WIDGET-A",
            name="Widget A",
            description="Standard widget.",
            quantity_on_hand=10,
            reorder_level=5,
            is_active=True,
            updated_at=ts,
        ),
        2: ProductRecord(
            id=2,
            sku="GADGET-B",
            name="Gadget B",
            description="Runs low often in the demo.",
            quantity_on_hand=3,
            reorder_level=10,
            is_active=True,
            updated_at=ts,
        ),
        3: ProductRecord(
            id=3,
            sku="CABLE-C",
            name="Cable C",
            description="Out of stock until someone receives a shipment.",
            quantity_on_hand=0,
            reorder_level=2,
            is_active=True,
            updated_at=ts,
        ),
    }


class ProductRepository:
    """In-memory catalog keyed by id and sku."""

    def __init__(self) -> None:
        self._by_id = dict(_seed_products())
        self._by_sku = {product.sku: product for product in self._by_id.values()}
        self._next_id = max(self._by_id.keys(), default=0) + 1

    def list_all(self) -> list[ProductRecord]:
        return list(self._by_id.values())

    def get_by_sku(self, sku: str) -> ProductRecord | None:
        return self._by_sku.get(sku)

    def sku_taken(self, sku: str) -> bool:
        return sku in self._by_sku

    def allocate_id(self) -> int:
        product_id = self._next_id
        self._next_id += 1
        return product_id

    def add(self, record: ProductRecord) -> ProductRecord:
        self._by_id[record.id] = record
        self._by_sku[record.sku] = record
        return record

    def save(self, record: ProductRecord) -> None:
        self._by_id[record.id] = record
        self._by_sku[record.sku] = record
