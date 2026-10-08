"""Stock levels and the movement ledger. Routes stay thin; change rules here."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.movement_repository import MovementRecord, MovementRepository
from app.repositories.product_repository import ProductRecord, ProductRepository
from app.repositories.user_repository import UserRepository
from app.schemas.product import (
    AdjustStock,
    MovementPage,
    MovementRead,
    MovementType,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ReceiveStock,
    SaleStock,
    normalize_sku,
)
from app.schemas.user import UserRead, UserRole


class InventoryService:
    def __init__(
        self,
        *,
        products: ProductRepository,
        movements: MovementRepository,
        users: UserRepository,
    ) -> None:
        self._products = products
        self._movements = movements
        self._users = users

    def list_products(
        self,
        actor: UserRead,
        *,
        low_stock: bool | None,
        include_inactive: bool,
        search: str | None,
    ) -> list[ProductRead]:
        if include_inactive and actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only a platform admin can include inactive products")
        rows = self._products.list_all()
        if not include_inactive:
            rows = [product for product in rows if product.is_active]
        if low_stock is True:
            rows = [product for product in rows if self._is_low_stock(product)]
        elif low_stock is False:
            rows = [product for product in rows if not self._is_low_stock(product)]
        if search is not None:
            needle = search.strip().casefold()
            if needle:
                rows = [
                    product
                    for product in rows
                    if needle in product.sku.casefold()
                    or needle in product.name.casefold()
                    or needle in product.description.casefold()
                ]
        rows.sort(key=lambda product: (product.sku,))
        return [self._to_product_read(product) for product in rows]

    def get_product(self, actor: UserRead, sku: str) -> ProductRead:
        return self._to_product_read(self._visible_product(actor, sku))

    def create_product(self, actor: UserRead, payload: ProductCreate) -> ProductRead:
        self._require_admin(actor, "Only a platform admin can create products")
        if self._products.sku_taken(payload.sku):
            raise ConflictError("Another product already uses this SKU")
        now = datetime.now(UTC)
        record = self._products.add(
            ProductRecord(
                id=self._products.allocate_id(),
                sku=payload.sku,
                name=payload.name,
                description=payload.description,
                quantity_on_hand=payload.quantity_on_hand,
                reorder_level=payload.reorder_level,
                is_active=True,
                updated_at=now,
            )
        )
        if record.quantity_on_hand > 0:
            self._record_movement(
                product=record,
                actor=actor,
                movement_type=MovementType.RECEIVE,
                delta=record.quantity_on_hand,
                quantity_after=record.quantity_on_hand,
                note="Opening balance",
            )
        return self._to_product_read(record)

    def update_product(self, actor: UserRead, sku: str, payload: ProductUpdate) -> ProductRead:
        self._require_admin(actor, "Only a platform admin can update products")
        record = self._require_product(sku)
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes:
            record.name = changes["name"]
        if "description" in changes:
            record.description = changes["description"]
        if "reorder_level" in changes:
            record.reorder_level = changes["reorder_level"]
        record.updated_at = datetime.now(UTC)
        self._products.save(record)
        return self._to_product_read(record)

    def deactivate_product(self, actor: UserRead, sku: str) -> ProductRead:
        self._require_admin(actor, "Only a platform admin can deactivate products")
        record = self._require_product(sku)
        if not record.is_active:
            return self._to_product_read(record)
        record.is_active = False
        record.updated_at = datetime.now(UTC)
        self._products.save(record)
        return self._to_product_read(record)

    def activate_product(self, actor: UserRead, sku: str) -> ProductRead:
        self._require_admin(actor, "Only a platform admin can activate products")
        record = self._require_product(sku)
        if record.is_active:
            return self._to_product_read(record)
        record.is_active = True
        record.updated_at = datetime.now(UTC)
        self._products.save(record)
        return self._to_product_read(record)

    def receive_stock(self, actor: UserRead, sku: str, payload: ReceiveStock) -> ProductRead:
        record = self._active_product(actor, sku)
        return self._apply_delta(
            record,
            actor,
            movement_type=MovementType.RECEIVE,
            delta=payload.quantity,
            note=payload.note.strip(),
        )

    def sale_stock(self, actor: UserRead, sku: str, payload: SaleStock) -> ProductRead:
        record = self._active_product(actor, sku)
        return self._apply_delta(
            record,
            actor,
            movement_type=MovementType.SALE,
            delta=-payload.quantity,
            note=payload.note.strip(),
        )

    def adjust_stock(self, actor: UserRead, sku: str, payload: AdjustStock) -> ProductRead:
        record = self._active_product(actor, sku)
        if payload.delta == 0:
            raise ConflictError("Adjustment delta cannot be zero")
        return self._apply_delta(
            record,
            actor,
            movement_type=MovementType.ADJUST,
            delta=payload.delta,
            note=payload.note.strip(),
        )

    def list_movements(
        self,
        actor: UserRead,
        sku: str,
        *,
        limit: int,
        offset: int,
    ) -> MovementPage:
        record = self._visible_product(actor, sku)
        rows = self._movements.list_for_product(record.id)
        window = rows[offset : offset + limit]
        return MovementPage(
            items=[self._to_movement_read(record, row) for row in window],
            total=len(rows),
            limit=limit,
            offset=offset,
        )

    def _apply_delta(
        self,
        record: ProductRecord,
        actor: UserRead,
        *,
        movement_type: MovementType,
        delta: int,
        note: str,
    ) -> ProductRead:
        new_qty = record.quantity_on_hand + delta
        if new_qty < 0:
            raise ConflictError(
                f"Not enough stock for {record.sku}. "
                f"On hand: {record.quantity_on_hand}, requested change: {delta}"
            )
        record.quantity_on_hand = new_qty
        record.updated_at = datetime.now(UTC)
        self._products.save(record)
        self._record_movement(
            product=record,
            actor=actor,
            movement_type=movement_type,
            delta=delta,
            quantity_after=new_qty,
            note=note,
        )
        return self._to_product_read(record)

    def _record_movement(
        self,
        *,
        product: ProductRecord,
        actor: UserRead,
        movement_type: MovementType,
        delta: int,
        quantity_after: int,
        note: str,
    ) -> None:
        self._movements.add(
            MovementRecord(
                id=self._movements.allocate_id(),
                product_id=product.id,
                movement_type=movement_type,
                delta=delta,
                quantity_after=quantity_after,
                note=note,
                actor_id=actor.id,
                created_at=datetime.now(UTC),
            )
        )

    def _visible_product(self, actor: UserRead, sku: str) -> ProductRecord:
        record = self._require_product(sku)
        if not record.is_active and actor.role is not UserRole.ADMIN:
            raise NotFoundError("Product", sku)
        return record

    def _active_product(self, actor: UserRead, sku: str) -> ProductRecord:
        record = self._visible_product(actor, sku)
        if not record.is_active:
            raise ConflictError("Stock movements are not allowed on inactive products")
        return record

    def _require_product(self, sku: str) -> ProductRecord:
        normalized = normalize_sku(sku)
        record = self._products.get_by_sku(normalized)
        if record is None:
            raise NotFoundError("Product", normalized)
        return record

    def _is_low_stock(self, record: ProductRecord) -> bool:
        return record.quantity_on_hand <= record.reorder_level

    def _to_product_read(self, record: ProductRecord) -> ProductRead:
        return ProductRead(
            id=record.id,
            sku=record.sku,
            name=record.name,
            description=record.description,
            quantity_on_hand=record.quantity_on_hand,
            reorder_level=record.reorder_level,
            is_active=record.is_active,
            is_low_stock=self._is_low_stock(record),
            updated_at=record.updated_at,
        )

    def _to_movement_read(self, product: ProductRecord, row: MovementRecord) -> MovementRead:
        actor = self._users.get_by_id(row.actor_id)
        return MovementRead(
            id=row.id,
            product_id=row.product_id,
            sku=product.sku,
            movement_type=row.movement_type,
            delta=row.delta,
            quantity_after=row.quantity_after,
            note=row.note,
            actor_id=row.actor_id,
            actor_name=actor.full_name if actor is not None else "Unknown",
            created_at=row.created_at,
        )

    def _require_admin(self, actor: UserRead, message: str) -> None:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError(message)
