"""Order placement, kitchen workflow, and privacy rules live here."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.menu_repository import MenuRepository
from app.repositories.order_repository import OrderLineRecord, OrderRecord, OrderRepository
from app.repositories.user_repository import UserRepository
from app.schemas.order import OrderCreate, OrderLineRead, OrderRead, OrderStatus
from app.schemas.user import UserRead, UserRole
from app.services.menu_service import MenuService

_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PLACED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


class OrderService:
    def __init__(
        self,
        *,
        orders: OrderRepository,
        menu: MenuRepository,
        users: UserRepository,
        menu_service: MenuService,
    ) -> None:
        self._orders = orders
        self._menu = menu
        self._users = users
        self._menu_service = menu_service

    def list_orders(
        self,
        actor: UserRead,
        *,
        status: OrderStatus | None,
    ) -> list[OrderRead]:
        if actor.role is UserRole.ADMIN:
            rows = self._orders.list_all()
        else:
            rows = self._orders.list_for_user(actor.id)
        if status is not None:
            rows = [row for row in rows if row.status is status]
        rows.sort(key=lambda row: (row.created_at, row.id), reverse=True)
        return [self._to_read(row) for row in rows]

    def get_order(self, actor: UserRead, order_id: int) -> OrderRead:
        row = self._orders.get(order_id)
        if row is None or not self._can_view(actor, row):
            raise NotFoundError("Order", order_id)
        return self._to_read(row)

    def place_order(self, actor: UserRead, payload: OrderCreate) -> OrderRead:
        lines: list[OrderLineRecord] = []
        total = 0
        for line in payload.lines:
            item = self._menu_service.orderable_record(line.menu_item_slug)
            total += item.price_cents * line.quantity
            lines.append(
                OrderLineRecord(
                    menu_item_id=item.id,
                    menu_item_slug=item.slug,
                    menu_item_name=item.name,
                    quantity=line.quantity,
                    unit_price_cents=item.price_cents,
                )
            )
        now = datetime.now(UTC)
        record = OrderRecord(
            id=self._orders.allocate_id(),
            user_id=actor.id,
            status=OrderStatus.PLACED,
            total_cents=total,
            note=payload.note.strip(),
            items=lines,
            created_at=now,
            updated_at=now,
        )
        self._orders.add(record)
        return self._to_read(record)

    def start_preparing(self, actor: UserRead, order_id: int) -> OrderRead:
        return self._transition(actor, order_id, OrderStatus.PREPARING, admin_only=True)

    def mark_ready(self, actor: UserRead, order_id: int) -> OrderRead:
        return self._transition(actor, order_id, OrderStatus.READY, admin_only=True)

    def complete(self, actor: UserRead, order_id: int) -> OrderRead:
        return self._transition(actor, order_id, OrderStatus.COMPLETED, owner_or_admin=True)

    def cancel(self, actor: UserRead, order_id: int) -> OrderRead:
        row = self._require_visible(actor, order_id)
        if row.status is OrderStatus.PLACED:
            if actor.role is not UserRole.ADMIN and row.user_id != actor.id:
                raise ForbiddenError()
            return self._apply_transition(row, OrderStatus.CANCELLED)
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only kitchen staff can cancel after preparation started")
        return self._apply_transition(row, OrderStatus.CANCELLED)

    def _transition(
        self,
        actor: UserRead,
        order_id: int,
        target: OrderStatus,
        *,
        admin_only: bool = False,
        owner_or_admin: bool = False,
    ) -> OrderRead:
        row = self._require_visible(actor, order_id)
        if admin_only and actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only kitchen staff can perform this action")
        if owner_or_admin:
            if actor.role is not UserRole.ADMIN and row.user_id != actor.id:
                raise ForbiddenError()
        return self._apply_transition(row, target)

    def _apply_transition(self, row: OrderRecord, target: OrderStatus) -> OrderRead:
        allowed = _TRANSITIONS.get(row.status, set())
        if target not in allowed:
            raise ConflictError(f"Cannot move from {row.status.value} to {target.value}")
        row.status = target
        row.updated_at = datetime.now(UTC)
        self._orders.save(row)
        return self._to_read(row)

    def _require_visible(self, actor: UserRead, order_id: int) -> OrderRecord:
        row = self._orders.get(order_id)
        if row is None or not self._can_view(actor, row):
            raise NotFoundError("Order", order_id)
        return row

    def _can_view(self, actor: UserRead, row: OrderRecord) -> bool:
        if actor.role is UserRole.ADMIN:
            return True
        return row.user_id == actor.id

    def _to_read(self, row: OrderRecord) -> OrderRead:
        user = self._users.get_by_id(row.user_id)
        items = [
            OrderLineRead(
                menu_item_id=line.menu_item_id,
                menu_item_slug=line.menu_item_slug,
                menu_item_name=line.menu_item_name,
                quantity=line.quantity,
                unit_price_cents=line.unit_price_cents,
                line_total_cents=line.quantity * line.unit_price_cents,
            )
            for line in row.items
        ]
        return OrderRead(
            id=row.id,
            user_id=row.user_id,
            customer_name=user.full_name if user else "Unknown",
            status=row.status,
            total_cents=row.total_cents,
            note=row.note,
            items=items,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
