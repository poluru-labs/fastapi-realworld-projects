"""Apply wallet events to the balance projection (pure functions for clarity)."""

from app.core.exceptions import ConflictError
from app.schemas.wallet import WalletEventType


def apply_event(*, balance_cents: int, event_type: str, payload: dict) -> int:
    if event_type == WalletEventType.WALLET_CREATED.value:
        return 0
    if event_type == WalletEventType.MONEY_DEPOSITED.value:
        amount = int(payload["amount_cents"])
        return balance_cents + amount
    if event_type == WalletEventType.MONEY_WITHDRAWN.value:
        amount = int(payload["amount_cents"])
        if balance_cents < amount:
            raise ConflictError("Insufficient funds")
        return balance_cents - amount
    if event_type == WalletEventType.TRANSFER_OUT.value:
        amount = int(payload["amount_cents"])
        if balance_cents < amount:
            raise ConflictError("Insufficient funds")
        return balance_cents - amount
    if event_type == WalletEventType.TRANSFER_IN.value:
        amount = int(payload["amount_cents"])
        return balance_cents + amount
    msg = f"Unknown event type: {event_type}"
    raise ConflictError(msg)
