from dataclasses import dataclass
from datetime import datetime

from app.schemas.product import MovementType


@dataclass
class MovementRecord:
    id: int
    product_id: int
    movement_type: MovementType
    delta: int
    quantity_after: int
    note: str
    actor_id: int
    created_at: datetime


def _seed_movements() -> dict[int, MovementRecord]:
    return {
        1: MovementRecord(
            id=1,
            product_id=1,
            movement_type=MovementType.RECEIVE,
            delta=10,
            quantity_after=10,
            note="Opening balance",
            actor_id=1,
            created_at=datetime.fromisoformat("2026-03-01T12:00:00+00:00"),
        ),
    }


class MovementRepository:
    """Append-only stock ledger in memory."""

    def __init__(self) -> None:
        self._movements = dict(_seed_movements())
        self._next_id = max(self._movements.keys(), default=0) + 1

    def list_for_product(self, product_id: int) -> list[MovementRecord]:
        rows = [row for row in self._movements.values() if row.product_id == product_id]
        return sorted(rows, key=lambda row: (row.created_at, row.id), reverse=True)

    def add(self, record: MovementRecord) -> MovementRecord:
        self._movements[record.id] = record
        return record

    def allocate_id(self) -> int:
        movement_id = self._next_id
        self._next_id += 1
        return movement_id
