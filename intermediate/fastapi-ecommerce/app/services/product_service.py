"""Product visibility, catalog filters, and admin publish workflow live here."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.product_repository import ProductRecord, ProductRepository
from app.repositories.user_repository import UserRepository
from app.schemas.product import (
    ProductCreate,
    ProductRead,
    ProductStatus,
    ProductUpdate,
    TagCount,
    slugify,
)
from app.schemas.user import UserRead, UserRole

_TRANSITIONS: dict[ProductStatus, set[ProductStatus]] = {
    ProductStatus.DRAFT: {ProductStatus.ACTIVE, ProductStatus.ARCHIVED},
    ProductStatus.ACTIVE: {ProductStatus.DRAFT, ProductStatus.ARCHIVED},
    ProductStatus.ARCHIVED: {ProductStatus.DRAFT},
}


def can_view_product(actor: UserRead | None, record: ProductRecord) -> bool:
    if record.status is ProductStatus.ACTIVE:
        return True
    if actor is None:
        return False
    if actor.role is UserRole.ADMIN:
        return True
    return actor.id == record.vendor_id


class ProductService:
    def __init__(
        self,
        *,
        products: ProductRepository,
        users: UserRepository,
    ) -> None:
        self._products = products
        self._users = users

    def list_products(
        self,
        actor: UserRead | None,
        *,
        status: ProductStatus | None,
        tag: str | None,
        query: str | None,
        max_price_cents: int | None,
    ) -> list[ProductRead]:
        rows = self._products.list_all()
        if actor is None or actor.role is not UserRole.ADMIN:
            rows = [product for product in rows if product.status is ProductStatus.ACTIVE]
        elif status is not None:
            rows = [product for product in rows if product.status is status]

        if tag is not None:
            needle = tag.strip().casefold()
            if needle:
                rows = [product for product in rows if needle in product.tags]
        if query is not None:
            needle = query.strip().casefold()
            if needle:
                rows = [
                    product
                    for product in rows
                    if needle in product.name.casefold()
                    or needle in product.summary.casefold()
                ]
        if max_price_cents is not None:
            rows = [product for product in rows if product.price_cents <= max_price_cents]

        rows.sort(key=lambda product: (product.name.casefold(), product.id))
        return [self._to_read(product) for product in rows]

    def get_product(self, actor: UserRead | None, slug: str) -> ProductRead:
        return self._to_read(self.visible_record(actor, slug))

    def visible_record(self, actor: UserRead | None, slug: str) -> ProductRecord:
        record = self._products.get_by_slug(slug)
        if record is None or not can_view_product(actor, record):
            raise NotFoundError("Product", slug)
        return record

    def purchasable_record(self, slug: str) -> ProductRecord:
        record = self._products.get_by_slug(slug)
        if record is None or record.status is not ProductStatus.ACTIVE:
            raise NotFoundError("Product", slug)
        return record

    def create_product(self, actor: UserRead, payload: ProductCreate) -> ProductRead:
        self._require_admin(actor, "Only a platform admin can create products")
        slug = payload.slug or slugify(payload.name)
        if not slug:
            raise ConflictError("Could not derive a slug from the name")
        if self._products.slug_taken(slug):
            raise ConflictError("Another product already uses this slug")
        now = datetime.now(UTC)
        record = ProductRecord(
            id=self._products.allocate_id(),
            slug=slug,
            name=payload.name,
            summary=payload.summary,
            description=payload.description,
            price_cents=payload.price_cents,
            stock=payload.stock,
            status=ProductStatus.DRAFT,
            vendor_id=actor.id,
            tags=payload.tags,
            created_at=now,
            updated_at=now,
            activated_at=None,
        )
        self._products.add(record)
        return self._to_read(record)

    def update_product(self, actor: UserRead, slug: str, payload: ProductUpdate) -> ProductRead:
        self._require_admin(actor, "Only a platform admin can update products")
        record = self._require_product(slug)
        if record.status is not ProductStatus.DRAFT:
            raise ConflictError("Only draft products accept content edits")
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes:
            record.name = changes["name"]
        if "summary" in changes:
            record.summary = changes["summary"]
        if "description" in changes:
            record.description = changes["description"]
        if "price_cents" in changes:
            record.price_cents = changes["price_cents"]
        if "stock" in changes:
            record.stock = changes["stock"]
        if "tags" in changes:
            record.tags = changes["tags"]
        record.updated_at = datetime.now(UTC)
        self._products.save(record)
        return self._to_read(record)

    def transition(self, actor: UserRead, slug: str, target: ProductStatus) -> ProductRead:
        self._require_admin(actor, "Only a platform admin can change product status")
        record = self._require_product(slug)
        allowed = _TRANSITIONS.get(record.status, set())
        if target not in allowed:
            raise ConflictError(f"Cannot move from {record.status.value} to {target.value}")
        now = datetime.now(UTC)
        record.status = target
        record.updated_at = now
        if target is ProductStatus.ACTIVE:
            record.activated_at = now
        if target is ProductStatus.DRAFT:
            record.activated_at = None
        self._products.save(record)
        return self._to_read(record)

    def list_tags(self) -> list[TagCount]:
        counts: dict[str, int] = {}
        for product in self._products.list_all():
            if product.status is not ProductStatus.ACTIVE:
                continue
            for tag in product.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return [TagCount(name=name, count=count) for name, count in sorted(counts.items())]

    def _require_product(self, slug: str) -> ProductRecord:
        record = self._products.get_by_slug(slug)
        if record is None:
            raise NotFoundError("Product", slug)
        return record

    def _to_read(self, record: ProductRecord) -> ProductRead:
        vendor = self._users.get_by_id(record.vendor_id)
        vendor_name = vendor.full_name if vendor else "Unknown"
        return ProductRead(
            id=record.id,
            slug=record.slug,
            name=record.name,
            summary=record.summary,
            description=record.description,
            price_cents=record.price_cents,
            stock=record.stock,
            status=record.status,
            vendor_id=record.vendor_id,
            vendor_name=vendor_name,
            tags=record.tags,
            created_at=record.created_at,
            updated_at=record.updated_at,
            activated_at=record.activated_at,
        )

    @staticmethod
    def _require_admin(actor: UserRead, message: str) -> None:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError(message)
