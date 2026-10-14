from datetime import date

from app.schemas.expense import ExpenseCreate, ExpenseRead, ExpenseUpdate, PaymentMethod

_SEED: dict[int, ExpenseRead] = {
    1: ExpenseRead(
        id=1,
        merchant="Corner Coffee",
        amount_cents=450,
        category="Food",
        spent_on=date.fromisoformat("2026-10-01"),
        payment_method=PaymentMethod.CARD,
        note="Morning latte",
        receipt_ref="RCPT-1001",
        flagged=False,
    ),
    2: ExpenseRead(
        id=2,
        merchant="Metro Transit",
        amount_cents=8500,
        category="Transport",
        spent_on=date.fromisoformat("2026-10-02"),
        payment_method=PaymentMethod.TRANSFER,
        note="Monthly pass",
        receipt_ref=None,
        flagged=False,
    ),
    3: ExpenseRead(
        id=3,
        merchant="Cloud Tools",
        amount_cents=1200,
        category="Software",
        spent_on=date.fromisoformat("2026-10-03"),
        payment_method=PaymentMethod.CARD,
        note="Needs receipt upload",
        receipt_ref=None,
        flagged=True,
    ),
}


class ExpenseRepository:
    """In-memory ledger. Restarting the process restores the seed expenses."""

    def __init__(self) -> None:
        self._expenses = dict(_SEED)
        self._next_id = max(self._expenses.keys(), default=0) + 1

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
        items = list(self._expenses.values())
        if category is not None:
            needle = category.strip().casefold()
            if needle:
                items = [row for row in items if row.category.casefold() == needle]
        if flagged is not None:
            items = [row for row in items if row.flagged is flagged]
        if payment_method is not None:
            items = [row for row in items if row.payment_method is payment_method]
        if from_date is not None:
            items = [row for row in items if row.spent_on >= from_date]
        if to_date is not None:
            items = [row for row in items if row.spent_on <= to_date]
        if min_amount_cents is not None:
            items = [row for row in items if row.amount_cents >= min_amount_cents]
        if max_amount_cents is not None:
            items = [row for row in items if row.amount_cents <= max_amount_cents]
        if search is not None:
            needle = search.strip().casefold()
            if needle:
                items = [
                    row
                    for row in items
                    if needle in row.merchant.casefold()
                    or needle in row.note.casefold()
                    or needle in row.category.casefold()
                    or (row.receipt_ref is not None and needle in row.receipt_ref.casefold())
                ]
        return sorted(items, key=lambda row: (row.flagged, row.spent_on, row.id), reverse=True)

    def list_for_summary(
        self,
        *,
        from_date: date | None,
        to_date: date | None,
        category: str | None,
    ) -> list[ExpenseRead]:
        return self.list_expenses(
            category=category,
            search=None,
            flagged=None,
            payment_method=None,
            from_date=from_date,
            to_date=to_date,
            min_amount_cents=None,
            max_amount_cents=None,
        )

    def list_categories(self) -> list[str]:
        categories = {row.category for row in self._expenses.values()}
        return sorted(categories, key=str.casefold)

    def get(self, expense_id: int) -> ExpenseRead | None:
        return self._expenses.get(expense_id)

    def receipt_ref_taken(self, receipt_ref: str, *, except_id: int | None = None) -> bool:
        normalized = receipt_ref.strip().casefold()
        for row in self._expenses.values():
            if except_id is not None and row.id == except_id:
                continue
            if row.receipt_ref is not None and row.receipt_ref.casefold() == normalized:
                return True
        return False

    def create(self, payload: ExpenseCreate) -> ExpenseRead:
        row = ExpenseRead(id=self._next_id, **payload.model_dump())
        self._expenses[self._next_id] = row
        self._next_id += 1
        return row

    def replace(self, expense_id: int, payload: ExpenseCreate) -> ExpenseRead | None:
        if expense_id not in self._expenses:
            return None
        row = ExpenseRead(id=expense_id, **payload.model_dump())
        self._expenses[expense_id] = row
        return row

    def update(self, expense_id: int, payload: ExpenseUpdate) -> ExpenseRead | None:
        existing = self._expenses.get(expense_id)
        if existing is None:
            return None
        data = existing.model_dump()
        changes = payload.model_dump(exclude_unset=True)
        if "receipt_ref" in changes:
            ref = changes["receipt_ref"]
            data["receipt_ref"] = None if ref is None else ref
            del changes["receipt_ref"]
        data.update(changes)
        row = ExpenseRead(**data)
        self._expenses[expense_id] = row
        return row

    def set_flagged(self, expense_id: int, flagged: bool) -> ExpenseRead | None:
        existing = self._expenses.get(expense_id)
        if existing is None:
            return None
        row = existing.model_copy(update={"flagged": flagged})
        self._expenses[expense_id] = row
        return row

    def delete(self, expense_id: int) -> ExpenseRead | None:
        return self._expenses.pop(expense_id, None)
