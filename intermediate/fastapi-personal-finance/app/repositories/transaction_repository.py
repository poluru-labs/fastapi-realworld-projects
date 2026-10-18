from dataclasses import dataclass
from datetime import date, datetime

from app.schemas.finance import TransactionStatus


@dataclass
class TransactionRecord:
    id: int
    account_id: int
    owner_id: int
    amount: float
    category: str
    payee: str
    memo: str
    occurred_on: date
    status: TransactionStatus
    created_at: datetime
    updated_at: datetime


def _seed_transactions() -> dict[int, TransactionRecord]:
    when = datetime.fromisoformat("2026-02-01T12:00:00+00:00")
    return {
        1: TransactionRecord(
            id=1,
            account_id=1,
            owner_id=1,
            amount=-45.2,
            category="groceries",
            payee="Corner Market",
            memo="Weekly shop",
            occurred_on=date(2026, 2, 1),
            status=TransactionStatus.POSTED,
            created_at=when,
            updated_at=when,
        ),
        2: TransactionRecord(
            id=2,
            account_id=1,
            owner_id=1,
            amount=3200.0,
            category="salary",
            payee="Employer Inc",
            memo="February pay",
            occurred_on=date(2026, 2, 1),
            status=TransactionStatus.POSTED,
            created_at=when,
            updated_at=when,
        ),
        3: TransactionRecord(
            id=3,
            account_id=1,
            owner_id=1,
            amount=-12.0,
            category="dining",
            payee="Cafe",
            memo="Draft coffee",
            occurred_on=date(2026, 2, 2),
            status=TransactionStatus.DRAFT,
            created_at=when,
            updated_at=when,
        ),
    }


class TransactionRepository:
    def __init__(self) -> None:
        self._by_id = dict(_seed_transactions())
        self._next_id = max(self._by_id.keys(), default=0) + 1

    def list_all(self) -> list[TransactionRecord]:
        return list(self._by_id.values())

    def list_for_account(self, account_id: int) -> list[TransactionRecord]:
        return [t for t in self._by_id.values() if t.account_id == account_id]

    def get(self, transaction_id: int) -> TransactionRecord | None:
        return self._by_id.get(transaction_id)

    def allocate_id(self) -> int:
        transaction_id = self._next_id
        self._next_id += 1
        return transaction_id

    def save(self, record: TransactionRecord) -> None:
        self._by_id[record.id] = record
