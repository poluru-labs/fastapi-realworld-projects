"""Account ownership, balances, and archive rules."""

from datetime import UTC, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.account_repository import AccountRecord, AccountRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.finance import (
    AccountCreate,
    AccountPage,
    AccountRead,
    AccountUpdate,
    TransactionStatus,
    slugify,
)
from app.schemas.user import UserRead, UserRole


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _balance(opening: float, account_id: int, transactions: TransactionRepository) -> float:
    total = opening
    for row in transactions.list_for_account(account_id):
        if row.status is TransactionStatus.POSTED:
            total += row.amount
    return round(total, 2)


def _can_view(actor: UserRead, record: AccountRecord) -> bool:
    if actor.role is UserRole.ADMIN:
        return True
    return actor.id == record.owner_id


class AccountService:
    def __init__(
        self,
        *,
        accounts: AccountRepository,
        transactions: TransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._transactions = transactions

    def list_all_admin(
        self,
        actor: UserRead,
        *,
        include_archived: bool,
        limit: int,
        offset: int,
    ) -> AccountPage:
        if actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Admin role required to list all accounts")
        rows = self._accounts.list_all()
        if not include_archived:
            rows = [a for a in rows if not a.archived]
        rows.sort(key=lambda a: (a.updated_at, a.id), reverse=True)
        return self._page(rows, limit=limit, offset=offset)

    def list_mine(
        self,
        actor: UserRead,
        *,
        include_archived: bool,
        limit: int,
        offset: int,
    ) -> AccountPage:
        rows = self._accounts.list_for_owner(actor.id)
        if not include_archived:
            rows = [a for a in rows if not a.archived]
        rows.sort(key=lambda a: (a.updated_at, a.id), reverse=True)
        return self._page(rows, limit=limit, offset=offset)

    def get_account(self, actor: UserRead, slug: str) -> AccountRead:
        record = self._require_visible(actor, slug)
        return self._to_read(record)

    def create_account(self, actor: UserRead, payload: AccountCreate) -> AccountRead:
        slug = payload.slug or slugify(payload.name)
        if self._accounts.slug_taken(slug):
            raise ConflictError("An account with this slug already exists")
        now = _utcnow()
        record = AccountRecord(
            id=self._accounts.allocate_id(),
            owner_id=actor.id,
            slug=slug,
            name=payload.name,
            account_type=payload.account_type,
            currency=payload.currency,
            opening_balance=round(payload.opening_balance, 2),
            archived=False,
            created_at=now,
            updated_at=now,
        )
        self._accounts.save(record)
        return self._to_read(record)

    def update_account(
        self,
        actor: UserRead,
        slug: str,
        payload: AccountUpdate,
    ) -> AccountRead:
        record = self._require_visible(actor, slug)
        if actor.role is not UserRole.ADMIN and actor.id != record.owner_id:
            raise ForbiddenError("Only the account owner can update it")
        if payload.name is not None:
            record.name = payload.name
        record.updated_at = _utcnow()
        self._accounts.save(record)
        return self._to_read(record)

    def archive(self, actor: UserRead, slug: str) -> AccountRead:
        record = self._require_visible(actor, slug)
        if actor.id != record.owner_id and actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only the owner can archive this account")
        if record.archived:
            raise ConflictError("Account is already archived")
        record.archived = True
        record.updated_at = _utcnow()
        self._accounts.save(record)
        return self._to_read(record)

    def restore(self, actor: UserRead, slug: str) -> AccountRead:
        record = self._require_visible(actor, slug)
        if actor.id != record.owner_id and actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only the owner can restore this account")
        if not record.archived:
            raise ConflictError("Account is not archived")
        record.archived = False
        record.updated_at = _utcnow()
        self._accounts.save(record)
        return self._to_read(record)

    def require_visible_account(self, actor: UserRead, slug: str) -> AccountRecord:
        return self._require_visible(actor, slug)

    def account_ids_for_actor(self, actor: UserRead) -> set[int]:
        if actor.role is UserRole.ADMIN:
            return {a.id for a in self._accounts.list_all()}
        return {a.id for a in self._accounts.list_for_owner(actor.id)}

    def _require_visible(self, actor: UserRead, slug: str) -> AccountRecord:
        record = self._accounts.get_by_slug(slug)
        if record is None or not _can_view(actor, record):
            raise NotFoundError("Account", slug)
        return record

    def _to_read(self, record: AccountRecord) -> AccountRead:
        return AccountRead(
            id=record.id,
            owner_id=record.owner_id,
            slug=record.slug,
            name=record.name,
            account_type=record.account_type,
            currency=record.currency,
            opening_balance=record.opening_balance,
            current_balance=_balance(record.opening_balance, record.id, self._transactions),
            archived=record.archived,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _page(self, rows: list[AccountRecord], *, limit: int, offset: int) -> AccountPage:
        total = len(rows)
        slice_ = rows[offset : offset + limit]
        items = [self._to_read(r) for r in slice_]
        return AccountPage(items=items, total=total, limit=limit, offset=offset)
