from datetime import date

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.expense_repository import ExpenseRepository
from app.schemas.expense import (
    CategoryTotal,
    ExpenseCreate,
    ExpenseRead,
    ExpenseSummary,
    ExpenseUpdate,
    PaymentMethod,
)


class ExpenseService:
    def __init__(self, repository: ExpenseRepository) -> None:
        self._repo = repository

    def list_expenses(
        self,
        *,
        category: str | None = None,
        search: str | None = None,
        flagged: bool | None = None,
        payment_method: PaymentMethod | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        min_amount_cents: int | None = None,
        max_amount_cents: int | None = None,
    ) -> list[ExpenseRead]:
        return self._repo.list_expenses(
            category=category,
            search=search,
            flagged=flagged,
            payment_method=payment_method,
            from_date=from_date,
            to_date=to_date,
            min_amount_cents=min_amount_cents,
            max_amount_cents=max_amount_cents,
        )

    def summarize(
        self,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        category: str | None = None,
    ) -> ExpenseSummary:
        rows = self._repo.list_for_summary(
            from_date=from_date,
            to_date=to_date,
            category=category,
        )
        totals: dict[str, CategoryTotal] = {}
        total_cents = 0
        for row in rows:
            total_cents += row.amount_cents
            bucket = totals.get(row.category)
            if bucket is None:
                totals[row.category] = CategoryTotal(
                    category=row.category,
                    total_cents=row.amount_cents,
                    count=1,
                )
            else:
                totals[row.category] = CategoryTotal(
                    category=row.category,
                    total_cents=bucket.total_cents + row.amount_cents,
                    count=bucket.count + 1,
                )
        by_category = sorted(totals.values(), key=lambda item: item.category.casefold())
        return ExpenseSummary(
            total_cents=total_cents,
            count=len(rows),
            by_category=by_category,
        )

    def list_categories(self) -> list[str]:
        return self._repo.list_categories()

    def get_expense(self, expense_id: int) -> ExpenseRead:
        row = self._repo.get(expense_id)
        if row is None:
            raise NotFoundError("Expense", expense_id)
        return row

    def create_expense(self, payload: ExpenseCreate) -> ExpenseRead:
        if payload.receipt_ref is not None and self._repo.receipt_ref_taken(payload.receipt_ref):
            raise ConflictError("Another expense already uses this receipt reference")
        return self._repo.create(payload)

    def replace_expense(self, expense_id: int, payload: ExpenseCreate) -> ExpenseRead:
        if payload.receipt_ref is not None and self._repo.receipt_ref_taken(
            payload.receipt_ref, except_id=expense_id
        ):
            raise ConflictError("Another expense already uses this receipt reference")
        row = self._repo.replace(expense_id, payload)
        if row is None:
            raise NotFoundError("Expense", expense_id)
        return row

    def update_expense(self, expense_id: int, payload: ExpenseUpdate) -> ExpenseRead:
        changes = payload.model_dump(exclude_unset=True)
        if "receipt_ref" in changes and changes["receipt_ref"] not in (None, ""):
            ref = str(changes["receipt_ref"])
            if self._repo.receipt_ref_taken(ref, except_id=expense_id):
                raise ConflictError("Another expense already uses this receipt reference")
        row = self._repo.update(expense_id, payload)
        if row is None:
            raise NotFoundError("Expense", expense_id)
        return row

    def flag_expense(self, expense_id: int) -> ExpenseRead:
        row = self._repo.set_flagged(expense_id, True)
        if row is None:
            raise NotFoundError("Expense", expense_id)
        return row

    def unflag_expense(self, expense_id: int) -> ExpenseRead:
        row = self._repo.set_flagged(expense_id, False)
        if row is None:
            raise NotFoundError("Expense", expense_id)
        return row

    def delete_expense(self, expense_id: int) -> ExpenseRead:
        row = self._repo.delete(expense_id)
        if row is None:
            raise NotFoundError("Expense", expense_id)
        return row
