from dataclasses import dataclass
from datetime import datetime

from app.schemas.finance import AccountType


@dataclass
class AccountRecord:
    id: int
    owner_id: int
    slug: str
    name: str
    account_type: AccountType
    currency: str
    opening_balance: float
    archived: bool
    created_at: datetime
    updated_at: datetime


def _seed_accounts() -> dict[int, AccountRecord]:
    created = datetime.fromisoformat("2026-01-15T09:00:00+00:00")
    return {
        1: AccountRecord(
            id=1,
            owner_id=1,
            slug="checking-main",
            name="Main checking",
            account_type=AccountType.CHECKING,
            currency="USD",
            opening_balance=1000.0,
            archived=False,
            created_at=created,
            updated_at=created,
        ),
        2: AccountRecord(
            id=2,
            owner_id=1,
            slug="savings-emergency",
            name="Emergency savings",
            account_type=AccountType.SAVINGS,
            currency="USD",
            opening_balance=5000.0,
            archived=False,
            created_at=created,
            updated_at=created,
        ),
    }


class AccountRepository:
    def __init__(self) -> None:
        self._by_id = dict(_seed_accounts())
        self._by_slug = {a.slug: a for a in self._by_id.values()}
        self._next_id = max(self._by_id.keys(), default=0) + 1

    def list_all(self) -> list[AccountRecord]:
        return list(self._by_id.values())

    def list_for_owner(self, owner_id: int) -> list[AccountRecord]:
        return [a for a in self._by_id.values() if a.owner_id == owner_id]

    def get_by_slug(self, slug: str) -> AccountRecord | None:
        return self._by_slug.get(slug)

    def get_by_id(self, account_id: int) -> AccountRecord | None:
        return self._by_id.get(account_id)

    def slug_taken(self, slug: str) -> bool:
        return slug in self._by_slug

    def allocate_id(self) -> int:
        account_id = self._next_id
        self._next_id += 1
        return account_id

    def save(self, record: AccountRecord) -> None:
        self._by_id[record.id] = record
        self._by_slug[record.slug] = record
