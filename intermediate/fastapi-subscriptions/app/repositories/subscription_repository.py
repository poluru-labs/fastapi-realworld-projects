from dataclasses import dataclass
from datetime import datetime

from app.schemas.subscription import SubscriptionStatus


@dataclass
class SubscriptionRecord:
    id: int
    user_id: int
    plan_id: int
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    created_at: datetime
    cancelled_at: datetime | None = None


class SubscriptionRepository:
    def __init__(self) -> None:
        self._rows: dict[int, SubscriptionRecord] = {}
        self._next_id = 1

    def list_all(self) -> list[SubscriptionRecord]:
        return list(self._rows.values())

    def get(self, subscription_id: int) -> SubscriptionRecord | None:
        return self._rows.get(subscription_id)

    def add(self, record: SubscriptionRecord) -> SubscriptionRecord:
        self._rows[record.id] = record
        return record

    def save(self, record: SubscriptionRecord) -> None:
        self._rows[record.id] = record

    def allocate_id(self) -> int:
        subscription_id = self._next_id
        self._next_id += 1
        return subscription_id

    def list_for_user(self, user_id: int) -> list[SubscriptionRecord]:
        return [row for row in self._rows.values() if row.user_id == user_id]

    def list_for_plan(self, plan_id: int) -> list[SubscriptionRecord]:
        return [row for row in self._rows.values() if row.plan_id == plan_id]

    def active_for_user_plan(self, *, user_id: int, plan_id: int) -> SubscriptionRecord | None:
        for row in self._rows.values():
            if row.user_id != user_id or row.plan_id != plan_id:
                continue
            if row.status is SubscriptionStatus.ACTIVE:
                return row
        return None

    def count_active_for_plan(self, plan_id: int) -> int:
        return sum(
            1
            for row in self._rows.values()
            if row.plan_id == plan_id and row.status is SubscriptionStatus.ACTIVE
        )
