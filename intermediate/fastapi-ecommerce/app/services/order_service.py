"""Checkout, stock decrement, and order privacy rules live here."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.cart_repository import CartRepository
from app.repositories.order_repository import OrderLineRecord, OrderRecord, OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.schemas.order import CheckoutCreate, OrderLineRead, OrderRead, OrderStatus
from app.schemas.product import ProductStatus
from app.schemas.user import UserRead, UserRole
from app.services.cart_service import CartService


class OrderService:
    def __init__(
        self,
        *,
        orders: OrderRepository,
        products: ProductRepository,
        carts: CartRepository,
        users: UserRepository,
        cart_service: CartService,
    ) -> None:
        self._orders = orders
        self._products = products
        self._carts = carts
        self._users = users
        self._cart_service = cart_service

    def list_orders(
        self,
        actor: UserRead,
        *,
        order_status: OrderStatus | None,
    ) -> list[OrderRead]:
        if actor.role is UserRole.ADMIN:
            rows = self._orders.list_all()
        else:
            rows = self._orders.list_for_user(actor.id)
        if order_status is not None:
            rows = [row for row in rows if row.status is order_status]
        rows.sort(key=lambda row: (row.created_at, row.id), reverse=True)
        return [self._to_read(row) for row in rows]

    def get_order(self, actor: UserRead, order_id: int) -> OrderRead:
        row = self._orders.get(order_id)
        if row is None or not self._can_view(actor, row):
            raise NotFoundError("Order", order_id)
        return self._to_read(row)

    def checkout(self, actor: UserRead, payload: CheckoutCreate) -> OrderRead:
        cart = self._cart_service.get_cart(actor)
        if not cart.items:
            raise ConflictError("Cart is empty")

        for item in cart.items:
            product = self._products.get(item.product_id)
            if product is None or product.status is not ProductStatus.ACTIVE:
                raise ConflictError("Cart contains a product that is no longer for sale")
            if item.quantity > product.stock:
                raise ConflictError("Insufficient stock for one or more cart lines")

        order_lines: list[OrderLineRecord] = []
        total = 0
        for item in cart.items:
            product = self._products.get(item.product_id)
            assert product is not None
            product.stock -= item.quantity
            self._products.save(product)
            order_lines.append(
                OrderLineRecord(
                    product_id=product.id,
                    product_slug=product.slug,
                    product_name=product.name,
                    quantity=item.quantity,
                    unit_price_cents=product.price_cents,
                )
            )
            total += item.quantity * product.price_cents

        now = datetime.now(UTC)
        record = OrderRecord(
            id=self._orders.allocate_id(),
            user_id=actor.id,
            status=OrderStatus.PLACED,
            total_cents=total,
            note=payload.note.strip(),
            items=order_lines,
            created_at=now,
        )
        self._orders.add(record)
        self._carts.clear(actor.id)
        return self._to_read(record)

    def cancel(self, actor: UserRead, order_id: int) -> OrderRead:
        row = self._orders.get(order_id)
        if row is None or not self._can_view(actor, row):
            raise NotFoundError("Order", order_id)
        if row.status is OrderStatus.CANCELLED:
            raise ConflictError("Order is already cancelled")
        if actor.role is not UserRole.ADMIN and row.user_id != actor.id:
            raise ForbiddenError()

        for line in row.items:
            product = self._products.get(line.product_id)
            if product is not None:
                product.stock += line.quantity
                self._products.save(product)

        row.status = OrderStatus.CANCELLED
        self._orders.save(row)
        return self._to_read(row)

    def _can_view(self, actor: UserRead, row: OrderRecord) -> bool:
        if actor.role is UserRole.ADMIN:
            return True
        return row.user_id == actor.id

    def _to_read(self, row: OrderRecord) -> OrderRead:
        user = self._users.get_by_id(row.user_id)
        items = [
            OrderLineRead(
                product_id=line.product_id,
                product_slug=line.product_slug,
                product_name=line.product_name,
                quantity=line.quantity,
                unit_price_cents=line.unit_price_cents,
                line_total_cents=line.quantity * line.unit_price_cents,
            )
            for line in row.items
        ]
        return OrderRead(
            id=row.id,
            user_id=row.user_id,
            buyer_name=user.full_name if user else "Unknown",
            status=row.status,
            total_cents=row.total_cents,
            items=items,
            created_at=row.created_at,
        )
