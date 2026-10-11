from dataclasses import dataclass, field
from datetime import datetime

from app.schemas.product import ProductStatus


@dataclass
class ProductRecord:
    id: int
    slug: str
    name: str
    summary: str
    description: str
    price_cents: int
    stock: int
    status: ProductStatus
    vendor_id: int
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    activated_at: datetime | None = None


def _seed_products() -> dict[int, ProductRecord]:
    return {
        1: ProductRecord(
            id=1,
            slug="usb-c-hub",
            name="USB-C Hub",
            summary="Seven ports for laptops and tablets.",
            description="HDMI, USB-A, and SD card in one compact hub.",
            price_cents=4999,
            stock=10,
            status=ProductStatus.ACTIVE,
            vendor_id=1,
            tags=["electronics", "accessories"],
            created_at=datetime.fromisoformat("2026-09-01T10:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-09-15T10:00:00+00:00"),
            activated_at=datetime.fromisoformat("2026-09-15T10:00:00+00:00"),
        ),
        2: ProductRecord(
            id=2,
            slug="draft-wireless-mouse",
            name="Draft wireless mouse",
            summary="Not visible in the public catalog yet.",
            description="Prototype listing for internal review.",
            price_cents=2999,
            stock=5,
            status=ProductStatus.DRAFT,
            vendor_id=1,
            tags=["internal"],
            created_at=datetime.fromisoformat("2026-09-02T10:00:00+00:00"),
            updated_at=datetime.fromisoformat("2026-09-02T10:00:00+00:00"),
            activated_at=None,
        ),
    }


class ProductRepository:
    def __init__(self) -> None:
        self._products = dict(_seed_products())
        self._by_slug = {product.slug: product for product in self._products.values()}
        self._next_id = max(self._products.keys(), default=0) + 1

    def list_all(self) -> list[ProductRecord]:
        return list(self._products.values())

    def get(self, product_id: int) -> ProductRecord | None:
        return self._products.get(product_id)

    def get_by_slug(self, slug: str) -> ProductRecord | None:
        return self._by_slug.get(slug)

    def slug_taken(self, slug: str, *, except_id: int | None = None) -> bool:
        existing = self._by_slug.get(slug)
        if existing is None:
            return False
        if except_id is not None and existing.id == except_id:
            return False
        return True

    def add(self, record: ProductRecord) -> ProductRecord:
        self._products[record.id] = record
        self._by_slug[record.slug] = record
        return record

    def save(self, record: ProductRecord) -> None:
        previous = self._products.get(record.id)
        if previous is not None and previous.slug != record.slug:
            self._by_slug.pop(previous.slug, None)
        self._products[record.id] = record
        self._by_slug[record.slug] = record

    def allocate_id(self) -> int:
        product_id = self._next_id
        self._next_id += 1
        return product_id
