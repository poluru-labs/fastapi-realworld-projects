from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.api.deps import get_current_user, get_transaction_service
from app.schemas.finance import (
    SLUG_PATTERN,
    TransactionCreate,
    TransactionPage,
    TransactionRead,
    TransactionStatus,
    TransactionUpdate,
)
from app.schemas.user import UserRead
from app.services.transaction_service import TransactionService

router = APIRouter()

Slug = Annotated[
    str,
    Path(
        pattern=SLUG_PATTERN.pattern,
        min_length=1,
        max_length=80,
        examples=["checking-main"],
    ),
]

_CREATE_EXAMPLES = {
    "expense": {
        "summary": "Draft expense",
        "value": {
            "amount": -18.75,
            "category": "transport",
            "payee": "Metro Transit",
            "memo": "Monthly pass",
            "occurred_on": "2026-02-03",
        },
    }
}


@router.get(
    "",
    response_model=TransactionPage,
    summary="List transactions on an account",
)
def list_transactions(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
    tx_status: Annotated[TransactionStatus | None, Query(alias="status")] = None,
    category: Annotated[str | None, Query(max_length=32)] = None,
    from_date: Annotated[date | None, Query()] = None,
    to_date: Annotated[date | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TransactionPage:
    return service.list_for_account(
        actor,
        slug,
        status=tx_status,
        category=category,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft transaction",
    description="Drafts do not affect **current_balance** until you **post** them.",
)
def create_transaction(
    slug: Slug,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
    payload: Annotated[TransactionCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> TransactionRead:
    return service.create_draft(actor, slug, payload)


@router.get(
    "/{transaction_id}",
    response_model=TransactionRead,
    summary="Get a transaction",
)
def get_transaction(
    slug: Slug,
    transaction_id: Annotated[int, Path(ge=1)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionRead:
    return service.get_transaction(actor, slug, transaction_id)


@router.patch(
    "/{transaction_id}",
    response_model=TransactionRead,
    summary="Update a draft transaction",
)
def update_transaction(
    slug: Slug,
    transaction_id: Annotated[int, Path(ge=1)],
    payload: TransactionUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionRead:
    return service.update_draft(actor, slug, transaction_id, payload)


@router.post(
    "/{transaction_id}/post",
    response_model=TransactionRead,
    summary="Post a draft transaction",
)
def post_transaction(
    slug: Slug,
    transaction_id: Annotated[int, Path(ge=1)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionRead:
    return service.post(actor, slug, transaction_id)


@router.post(
    "/{transaction_id}/void",
    response_model=TransactionRead,
    summary="Void a posted transaction",
)
def void_transaction(
    slug: Slug,
    transaction_id: Annotated[int, Path(ge=1)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionRead:
    return service.void(actor, slug, transaction_id)
