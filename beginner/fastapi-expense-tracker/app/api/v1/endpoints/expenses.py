from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_expense_service
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseDeleteResponse,
    ExpenseRead,
    ExpenseSummary,
    ExpenseUpdate,
    PaymentMethod,
)
from app.services.expense_service import ExpenseService

router = APIRouter()

_CREATE_EXAMPLES = {
    "coffee": {
        "summary": "Card purchase with receipt",
        "description": "receipt_ref must be unique when provided.",
        "value": {
            "merchant": "Corner Coffee",
            "amount_cents": 550,
            "category": "Food",
            "spent_on": "2026-10-10",
            "payment_method": "card",
            "note": "Team standup",
            "receipt_ref": "RCPT-2001",
        },
    },
    "cash": {
        "summary": "Cash expense",
        "value": {
            "merchant": "Farmers Market",
            "amount_cents": 3200,
            "category": "Food",
            "spent_on": "2026-10-11",
            "payment_method": "cash",
        },
    },
}


@router.get(
    "/categories",
    response_model=list[str],
    summary="List distinct categories",
)
def list_categories(service: Annotated[ExpenseService, Depends(get_expense_service)]) -> list[str]:
    return service.list_categories()


@router.get(
    "/summary",
    response_model=ExpenseSummary,
    summary="Totals for a date range",
    description=(
        "Returns overall `total_cents`, row `count`, and per-category breakdown. "
        "Optional `from_date`, `to_date`, and `category` filters match the list endpoint."
    ),
)
def summarize_expenses(
    service: Annotated[ExpenseService, Depends(get_expense_service)],
    from_date: Annotated[
        date | None,
        Query(description="Inclusive start date (YYYY-MM-DD)."),
    ] = None,
    to_date: Annotated[
        date | None,
        Query(description="Inclusive end date (YYYY-MM-DD)."),
    ] = None,
    category: Annotated[str | None, Query(description="Exact category match.")] = None,
) -> ExpenseSummary:
    return service.summarize(from_date=from_date, to_date=to_date, category=category)


@router.get(
    "",
    response_model=list[ExpenseRead],
    summary="List expenses",
    description=(
        "Flagged rows appear first, then newest `spent_on`. "
        "Filter with `category`, `search`, `flagged`, `payment_method`, date range, and amount."
    ),
)
def list_expenses(
    service: Annotated[ExpenseService, Depends(get_expense_service)],
    category: Annotated[str | None, Query(description="Exact category (case insensitive).")] = None,
    search: Annotated[
        str | None,
        Query(description="Search merchant, note, category, receipt."),
    ] = None,
    flagged: Annotated[bool | None, Query(description="Filter flagged for review.")] = None,
    payment_method: Annotated[
        PaymentMethod | None,
        Query(description="card, cash, or transfer."),
    ] = None,
    from_date: Annotated[date | None, Query(description="Inclusive start date.")] = None,
    to_date: Annotated[date | None, Query(description="Inclusive end date.")] = None,
    min_amount_cents: Annotated[int | None, Query(ge=1)] = None,
    max_amount_cents: Annotated[int | None, Query(ge=1)] = None,
) -> list[ExpenseRead]:
    return service.list_expenses(
        category=category,
        search=search,
        flagged=flagged,
        payment_method=payment_method,
        from_date=from_date,
        to_date=to_date,
        min_amount_cents=min_amount_cents,
        max_amount_cents=max_amount_cents,
    )


@router.get("/{expense_id}", response_model=ExpenseRead, summary="Get one expense")
def get_expense(
    expense_id: int,
    service: Annotated[ExpenseService, Depends(get_expense_service)],
) -> ExpenseRead:
    return service.get_expense(expense_id)


@router.post(
    "",
    response_model=ExpenseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record an expense",
)
def create_expense(
    service: Annotated[ExpenseService, Depends(get_expense_service)],
    payload: Annotated[ExpenseCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> ExpenseRead:
    return service.create_expense(payload)


@router.put("/{expense_id}", response_model=ExpenseRead, summary="Replace an expense")
def replace_expense(
    expense_id: int,
    payload: ExpenseCreate,
    service: Annotated[ExpenseService, Depends(get_expense_service)],
) -> ExpenseRead:
    return service.replace_expense(expense_id, payload)


@router.patch("/{expense_id}", response_model=ExpenseRead, summary="Partial update")
def update_expense(
    expense_id: int,
    service: Annotated[ExpenseService, Depends(get_expense_service)],
    payload: ExpenseUpdate,
) -> ExpenseRead:
    return service.update_expense(expense_id, payload)


@router.post("/{expense_id}/flag", response_model=ExpenseRead, summary="Flag for review")
def flag_expense(
    expense_id: int,
    service: Annotated[ExpenseService, Depends(get_expense_service)],
) -> ExpenseRead:
    return service.flag_expense(expense_id)


@router.post("/{expense_id}/unflag", response_model=ExpenseRead, summary="Clear review flag")
def unflag_expense(
    expense_id: int,
    service: Annotated[ExpenseService, Depends(get_expense_service)],
) -> ExpenseRead:
    return service.unflag_expense(expense_id)


@router.delete("/{expense_id}", response_model=ExpenseDeleteResponse, summary="Delete an expense")
def delete_expense(
    expense_id: int,
    service: Annotated[ExpenseService, Depends(get_expense_service)],
) -> ExpenseDeleteResponse:
    removed = service.delete_expense(expense_id)
    return ExpenseDeleteResponse(expense=removed)
