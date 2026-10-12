from typing import Annotated

from fastapi import APIRouter, Body, status

from app.api.deps import CurrentUser, DbSession, IdempotencyKey
from app.schemas.wallet import (
    MoneyCommand,
    TransferCreate,
    TransferResult,
    WalletCreate,
    WalletEventRead,
    WalletRead,
)
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/wallets", tags=["wallets"])

_CREATE_EXAMPLES = {
    "personal": {
        "summary": "USD checking wallet",
        "value": {"name": "Personal checking", "currency": "USD"},
    }
}

_DEPOSIT_EXAMPLES = {
    "paycheck": {
        "summary": "Deposit with optimistic version",
        "description": (
            "Send the `version` from your last `GET` as `expected_version`. "
            "Retries must reuse the same **Idempotency-Key** header."
        ),
        "value": {
            "amount_cents": 2500,
            "expected_version": 1,
            "memo": "Paycheck",
        },
    }
}

_TRANSFER_EXAMPLES = {
    "peer": {
        "summary": "Move money between your wallets",
        "value": {
            "from_wallet_id": "00000000-0000-0000-0000-000000000001",
            "to_wallet_id": "00000000-0000-0000-0000-000000000002",
            "amount_cents": 500,
            "expected_version": 3,
            "memo": "Split dinner",
        },
    }
}


@router.get(
    "",
    response_model=list[WalletRead],
    summary="List wallets",
    description="Signed-in users see their wallets. Platform admins see every wallet.",
)
async def list_wallets(user: CurrentUser, session: DbSession) -> list[WalletRead]:
    return await WalletService(session).list_wallets(user)


@router.get(
    "/{wallet_id}",
    response_model=WalletRead,
    summary="Get wallet balance (projection)",
    description="Another user's wallet id returns **404**, not **403**.",
)
async def get_wallet(wallet_id: str, user: CurrentUser, session: DbSession) -> WalletRead:
    return await WalletService(session).get_wallet(user, wallet_id)


@router.get(
    "/{wallet_id}/events",
    response_model=list[WalletEventRead],
    summary="Read the append-only event stream",
    description=(
        "Events are ordered by `sequence` per wallet. "
        "The `balance_cents` on the wallet row is a projection of this stream."
    ),
)
async def list_wallet_events(
    wallet_id: str,
    user: CurrentUser,
    session: DbSession,
) -> list[WalletEventRead]:
    return await WalletService(session).list_events(user, wallet_id)


@router.post(
    "",
    response_model=WalletRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a wallet",
)
async def create_wallet(
    user: CurrentUser,
    session: DbSession,
    idempotency_key: IdempotencyKey,
    payload: Annotated[WalletCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> WalletRead:
    return await WalletService(session).create_wallet(
        user,
        payload,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/{wallet_id}/deposits",
    response_model=WalletRead,
    summary="Deposit money",
)
async def deposit(
    wallet_id: str,
    user: CurrentUser,
    session: DbSession,
    idempotency_key: IdempotencyKey,
    payload: Annotated[MoneyCommand, Body(openapi_examples=_DEPOSIT_EXAMPLES)],
) -> WalletRead:
    return await WalletService(session).deposit(
        user,
        wallet_id,
        payload,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/{wallet_id}/withdrawals",
    response_model=WalletRead,
    summary="Withdraw money",
)
async def withdraw(
    wallet_id: str,
    user: CurrentUser,
    session: DbSession,
    idempotency_key: IdempotencyKey,
    payload: Annotated[MoneyCommand, Body(openapi_examples=_DEPOSIT_EXAMPLES)],
) -> WalletRead:
    return await WalletService(session).withdraw(
        user,
        wallet_id,
        payload,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/transfers",
    response_model=TransferResult,
    summary="Transfer between wallets",
    description=(
        "Appends **transfer_out** and **transfer_in** events in one database transaction. "
        "Both wallets must share the same currency."
    ),
)
async def transfer(
    user: CurrentUser,
    session: DbSession,
    idempotency_key: IdempotencyKey,
    payload: Annotated[TransferCreate, Body(openapi_examples=_TRANSFER_EXAMPLES)],
) -> TransferResult:
    return await WalletService(session).transfer(
        user,
        payload,
        idempotency_key=idempotency_key,
    )
