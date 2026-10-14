from dataclasses import dataclass, field
from datetime import datetime

from app.schemas.order import OrderStatus


@dataclass
class OrderLineRecord:
    menu_item_id: int
    menu_item_slug: str
    menu_item_name: str
    quantity: int
    unit_price_cents: int


@dataclass
class OrderRecord:
    id: int
    user_id: int
    status: OrderStatus
    total_cents: int
    note: str
    items: list[OrderLineRecord] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class OrderRepository:
    def __init__(self) -> None:
        self._orders: dict[int, OrderRecord] = {}
        self._next_id = 1

    def list_all(self) -> list[OrderRecord]:
        return list(self._orders.values())

    def get(self, order_id: int) -> OrderRecord | None:
        return self._orders.get(order_id)

    def list_for_user(self, user_id: int) -> list[OrderRecord]:
        return [row for row in self._orders.values() if row.user_id == user_id]

    def add(self, record: OrderRecord) -> OrderRecord:
        self._orders[record.id] = record
        return record

    def save(self, record: OrderRecord) -> None:
        self._orders[record.id] = record

    def allocate_id(self) -> int:
        order_id = self._next_id
        self._next_id += 1
        return order_id
