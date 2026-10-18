from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_transaction_service
from app.schemas.finance import CategorySpend
from app.schemas.user import UserRead
from app.services.transaction_service import TransactionService

router = APIRouter()


@router.get(
    "/categories",
    response_model=list[CategorySpend],
    summary="Spending totals by category",
    description=(
        "Sums **posted** expenses (negative amounts) across your accounts. "
        "Optional `from_date` / `to_date` filter on **occurred_on**."
    ),
)
def spending_by_category(
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
    from_date: Annotated[date | None, Query()] = None,
    to_date: Annotated[date | None, Query()] = None,
) -> list[CategorySpend]:
    return service.spending_by_category(actor, from_date=from_date, to_date=to_date)
