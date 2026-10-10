"""Idempotency, inventory reservation, outbox writes, and version checks live here."""

import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import request_id_var
from app.models.idempotency import IdempotencyRecord
from app.models.order import Order, OrderItem
from app.models.order import OrderStatus as ModelOrderStatus
from app.models.outbox import OutboxEvent
from app.repositories.idempotency_repository import IdempotencyRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order import OrderCreate, OrderItemRead, OrderRead, OrderStatus
from app.schemas.user import UserRead, UserRole

_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.FULFILLED, OrderStatus.CANCELLED},
    OrderStatus.FULFILLED: set(),
    OrderStatus.CANCELLED: set(),
}


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._products = ProductRepository(session)
        self._outbox = OutboxRepository(session)
        self._idempotency = IdempotencyRepository(session)

    async def list_orders(self, actor: UserRead) -> list[OrderRead]:
        if actor.role is UserRole.ADMIN:
            rows = await self._orders.list_all()
        else:
            rows = await self._orders.list_for_user(actor.id)
        return [self._to_read(row) for row in rows]

    async def get_order(self, actor: UserRead, order_id: int) -> OrderRead:
        row = await self._orders.get_with_items(order_id)
        if row is None or not self._can_view(actor, row):
            raise NotFoundError("Order", order_id)
        return self._to_read(row)

    async def create_order(
        self,
        actor: UserRead,
        payload: OrderCreate,
        *,
        idempotency_key: str,
    ) -> OrderRead:
        cached = await self._idempotency.get(idempotency_key)
        if cached is not None:
            if cached.user_id != actor.id:
                raise ConflictError("Idempotency key belongs to another user")
            return OrderRead.model_validate_json(cached.response_json)

        correlation_id = request_id_var.get("-")
        line_specs: list[tuple[str, int, int]] = []
        total = 0
        for line in payload.items:
            product = await self._products.get_by_sku(line.sku)
            if product is None:
                raise NotFoundError("Product", line.sku)
            line_total = product.price_cents * line.quantity
            total += line_total
            line_specs.append((line.sku, line.quantity, product.price_cents))

        for sku, quantity, _ in line_specs:
            reserved = await self._products.reserve(sku=sku, quantity=quantity)
            if not reserved:
                raise ConflictError(f"Insufficient stock for {sku}")

        order = Order(
            user_id=actor.id,
            status=ModelOrderStatus.PENDING.value,
            version=1,
            correlation_id=correlation_id,
            total_cents=total,
            items=[
                OrderItem(product_sku=sku, quantity=qty, unit_price_cents=price)
                for sku, qty, price in line_specs
            ],
        )
        order = await self._orders.add(order)

        await self._outbox.add(
            OutboxEvent(
                event_type="order.created",
                aggregate_id=order.id,
                payload_json=json.dumps(
                    {"order_id": order.id, "user_id": actor.id, "total_cents": total}
                ),
            )
        )

        response = self._to_read(order)
        await self._idempotency.save(
            IdempotencyRecord(
                key=idempotency_key,
                user_id=actor.id,
                response_json=response.model_dump_json(),
                status_code=201,
            )
        )
        await self._session.commit()
        return response

    async def pay(self, actor: UserRead, order_id: int, *, expected_version: int) -> OrderRead:
        return await self._transition(
            actor,
            order_id,
            target=OrderStatus.PAID,
            expected_version=expected_version,
            outbox_type="order.paid",
        )

    async def fulfill(
        self,
        actor: UserRead,
        order_id: int,
        *,
        expected_version: int,
    ) -> OrderRead:
        return await self._transition(
            actor,
            order_id,
            target=OrderStatus.FULFILLED,
            expected_version=expected_version,
            outbox_type="order.fulfilled",
        )

    async def cancel(
        self,
        actor: UserRead,
        order_id: int,
        *,
        expected_version: int,
    ) -> OrderRead:
        order = await self._require_order(actor, order_id)
        self._check_version(order, expected_version)
        current = OrderStatus(order.status)
        if current is OrderStatus.CANCELLED:
            raise ConflictError("Order is already cancelled")
        if current not in (OrderStatus.PENDING, OrderStatus.PAID):
            raise ConflictError(f"Cannot cancel from status {current.value}")

        for item in order.items:
            await self._products.release(sku=item.product_sku, quantity=item.quantity)

        order.status = OrderStatus.CANCELLED.value
        order.version += 1
        order.updated_at = datetime.now(UTC)

        await self._outbox.add(
            OutboxEvent(
                event_type="order.cancelled",
                aggregate_id=order.id,
                payload_json=json.dumps({"order_id": order.id, "user_id": order.user_id}),
            )
        )
        await self._session.commit()
        refreshed = await self._orders.get_with_items(order.id)
        assert refreshed is not None
        return self._to_read(refreshed)

    async def _transition(
        self,
        actor: UserRead,
        order_id: int,
        *,
        target: OrderStatus,
        expected_version: int,
        outbox_type: str,
    ) -> OrderRead:
        order = await self._require_order(actor, order_id)
        self._check_version(order, expected_version)
        current = OrderStatus(order.status)
        allowed = _TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ConflictError(f"Cannot move from {current.value} to {target.value}")

        order.status = target.value
        order.version += 1
        order.updated_at = datetime.now(UTC)

        await self._outbox.add(
            OutboxEvent(
                event_type=outbox_type,
                aggregate_id=order.id,
                payload_json=json.dumps({"order_id": order.id, "status": target.value}),
            )
        )
        await self._session.commit()
        refreshed = await self._orders.get_with_items(order.id)
        assert refreshed is not None
        return self._to_read(refreshed)

    async def _require_order(self, actor: UserRead, order_id: int) -> Order:
        order = await self._orders.get_with_items(order_id)
        if order is None or not self._can_view(actor, order):
            raise NotFoundError("Order", order_id)
        return order

    @staticmethod
    def _check_version(order: Order, expected_version: int) -> None:
        if order.version != expected_version:
            raise ConflictError("Order version mismatch — refresh and retry")

    @staticmethod
    def _can_view(actor: UserRead, order: Order) -> bool:
        if actor.role is UserRole.ADMIN:
            return True
        return order.user_id == actor.id

    @staticmethod
    def _to_read(order: Order) -> OrderRead:
        return OrderRead(
            id=order.id,
            user_id=order.user_id,
            status=OrderStatus(order.status),
            version=order.version,
            correlation_id=order.correlation_id,
            total_cents=order.total_cents,
            items=[
                OrderItemRead(
                    id=item.id,
                    product_sku=item.product_sku,
                    quantity=item.quantity,
                    unit_price_cents=item.unit_price_cents,
                    line_total_cents=item.quantity * item.unit_price_cents,
                )
                for item in order.items
            ],
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
