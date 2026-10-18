"""Transaction drafts, posting, voiding, and spending summaries."""

from datetime import UTC, date, datetime

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.transaction_repository import TransactionRecord, TransactionRepository
from app.schemas.finance import (
    CategorySpend,
    TransactionCreate,
    TransactionPage,
    TransactionRead,
    TransactionStatus,
    TransactionUpdate,
)
from app.schemas.user import UserRead, UserRole
from app.services.account_service import AccountService


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class TransactionService:
    def __init__(
        self,
        *,
        accounts: AccountService,
        transactions: TransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._transactions = transactions

    def list_for_account(
        self,
        actor: UserRead,
        account_slug: str,
        *,
        status: TransactionStatus | None,
        category: str | None,
        from_date: date | None,
        to_date: date | None,
        limit: int,
        offset: int,
    ) -> TransactionPage:
        account = self._accounts.require_visible_account(actor, account_slug)
        rows = self._transactions.list_for_account(account.id)
        if status is not None:
            rows = [t for t in rows if t.status is status]
        if category is not None:
            needle = category.strip().casefold()
            rows = [t for t in rows if t.category == needle]
        if from_date is not None:
            rows = [t for t in rows if t.occurred_on >= from_date]
        if to_date is not None:
            rows = [t for t in rows if t.occurred_on <= to_date]
        rows.sort(key=lambda t: (t.occurred_on, t.id), reverse=True)
        total = len(rows)
        slice_ = rows[offset : offset + limit]
        items = [TransactionRead.model_validate(r) for r in slice_]
        return TransactionPage(items=items, total=total, limit=limit, offset=offset)

    def get_transaction(
        self,
        actor: UserRead,
        account_slug: str,
        transaction_id: int,
    ) -> TransactionRead:
        return TransactionRead.model_validate(
            self._require_visible(actor, account_slug, transaction_id)
        )

    def create_draft(
        self,
        actor: UserRead,
        account_slug: str,
        payload: TransactionCreate,
    ) -> TransactionRead:
        account = self._accounts.require_visible_account(actor, account_slug)
        if account.archived:
            raise ConflictError("Cannot add transactions to an archived account")
        if actor.id != account.owner_id and actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only the account owner can create transactions")
        now = _utcnow()
        record = TransactionRecord(
            id=self._transactions.allocate_id(),
            account_id=account.id,
            owner_id=account.owner_id,
            amount=round(payload.amount, 2),
            category=payload.category,
            payee=payload.payee,
            memo=payload.memo,
            occurred_on=payload.occurred_on,
            status=TransactionStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
        self._transactions.save(record)
        return TransactionRead.model_validate(record)

    def update_draft(
        self,
        actor: UserRead,
        account_slug: str,
        transaction_id: int,
        payload: TransactionUpdate,
    ) -> TransactionRead:
        record = self._require_visible(actor, account_slug, transaction_id)
        if record.status is not TransactionStatus.DRAFT:
            raise ConflictError("Only draft transactions can be edited")
        if actor.id != record.owner_id and actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only the owner can edit this transaction")
        if payload.amount is not None:
            record.amount = round(payload.amount, 2)
        if payload.category is not None:
            record.category = payload.category
        if payload.payee is not None:
            record.payee = payload.payee
        if payload.memo is not None:
            record.memo = payload.memo
        if payload.occurred_on is not None:
            record.occurred_on = payload.occurred_on
        record.updated_at = _utcnow()
        self._transactions.save(record)
        return TransactionRead.model_validate(record)

    def post(
        self,
        actor: UserRead,
        account_slug: str,
        transaction_id: int,
    ) -> TransactionRead:
        record = self._require_visible(actor, account_slug, transaction_id)
        if actor.id != record.owner_id and actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only the owner can post this transaction")
        if record.status is not TransactionStatus.DRAFT:
            raise ConflictError("Only draft transactions can be posted")
        record.status = TransactionStatus.POSTED
        record.updated_at = _utcnow()
        self._transactions.save(record)
        return TransactionRead.model_validate(record)

    def void(
        self,
        actor: UserRead,
        account_slug: str,
        transaction_id: int,
    ) -> TransactionRead:
        record = self._require_visible(actor, account_slug, transaction_id)
        if actor.id != record.owner_id and actor.role is not UserRole.ADMIN:
            raise ForbiddenError("Only the owner can void this transaction")
        if record.status is not TransactionStatus.POSTED:
            raise ConflictError("Only posted transactions can be voided")
        record.status = TransactionStatus.VOIDED
        record.updated_at = _utcnow()
        self._transactions.save(record)
        return TransactionRead.model_validate(record)

    def spending_by_category(
        self,
        actor: UserRead,
        *,
        from_date: date | None,
        to_date: date | None,
    ) -> list[CategorySpend]:
        account_ids = self._accounts.account_ids_for_actor(actor)

        totals: dict[str, float] = {}
        for row in self._transactions.list_all():
            if row.account_id not in account_ids:
                continue
            if row.status is not TransactionStatus.POSTED or row.amount >= 0:
                continue
            if from_date is not None and row.occurred_on < from_date:
                continue
            if to_date is not None and row.occurred_on > to_date:
                continue
            totals[row.category] = totals.get(row.category, 0.0) + abs(row.amount)

        return [
            CategorySpend(category=name, total_spent=round(amount, 2))
            for name, amount in sorted(totals.items(), key=lambda item: (-item[1], item[0]))
        ]

    def _require_visible(
        self,
        actor: UserRead,
        account_slug: str,
        transaction_id: int,
    ) -> TransactionRecord:
        account = self._accounts.require_visible_account(actor, account_slug)
        record = self._transactions.get(transaction_id)
        if record is None or record.account_id != account.id:
            raise NotFoundError("Transaction", transaction_id)
        if actor.role is not UserRole.ADMIN and actor.id != record.owner_id:
            raise NotFoundError("Transaction", transaction_id)
        return record
