"""Append-only wallet events, projections, and optimistic concurrency."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.wallet import Wallet, WalletEvent
from app.repositories.idempotency_repository import IdempotencyRepository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.user import UserRead, UserRole
from app.schemas.wallet import (
    MoneyCommand,
    TransferCreate,
    TransferResult,
    WalletCreate,
    WalletEventRead,
    WalletEventType,
    WalletRead,
)
from app.services.wallet_projection import apply_event


class WalletService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._wallets = WalletRepository(session)
        self._idempotency = IdempotencyRepository(session)

    async def list_wallets(self, actor: UserRead) -> list[WalletRead]:
        if actor.role is UserRole.ADMIN:
            rows = await self._wallets.list_all()
        else:
            rows = await self._wallets.list_for_owner(actor.id)
        return [WalletRead.model_validate(row) for row in rows]

    async def get_wallet(self, actor: UserRead, wallet_id: str) -> WalletRead:
        row = await self._require_visible(actor, wallet_id)
        return WalletRead.model_validate(row)

    async def list_events(self, actor: UserRead, wallet_id: str) -> list[WalletEventRead]:
        await self._require_visible(actor, wallet_id)
        rows = await self._wallets.list_events(wallet_id)
        return [WalletEventRead.model_validate(row) for row in rows]

    async def create_wallet(
        self,
        actor: UserRead,
        payload: WalletCreate,
        *,
        idempotency_key: str,
    ) -> WalletRead:
        cached = await self._load_idempotent(actor, idempotency_key)
        if cached is not None:
            return cached

        wallet_id = str(uuid4())
        wallet = Wallet(
            id=wallet_id,
            owner_id=actor.id,
            name=payload.name,
            currency=payload.currency,
            balance_cents=0,
            version=0,
        )
        await self._wallets.add(wallet)
        await self._append(
            wallet,
            WalletEventType.WALLET_CREATED,
            {
                "name": payload.name,
                "currency": payload.currency,
                "owner_id": actor.id,
            },
        )
        result = WalletRead.model_validate(wallet)
        await self._store_idempotent(actor, idempotency_key, result)
        await self._session.commit()
        return result

    async def deposit(
        self,
        actor: UserRead,
        wallet_id: str,
        payload: MoneyCommand,
        *,
        idempotency_key: str,
    ) -> WalletRead:
        cached = await self._load_idempotent(actor, idempotency_key)
        if cached is not None:
            return cached

        wallet = await self._locked_wallet(actor, wallet_id)
        self._check_version(wallet, payload.expected_version)
        await self._append(
            wallet,
            WalletEventType.MONEY_DEPOSITED,
            {
                "amount_cents": payload.amount_cents,
                "memo": payload.memo,
            },
        )
        result = WalletRead.model_validate(wallet)
        await self._store_idempotent(actor, idempotency_key, result)
        await self._session.commit()
        return result

    async def withdraw(
        self,
        actor: UserRead,
        wallet_id: str,
        payload: MoneyCommand,
        *,
        idempotency_key: str,
    ) -> WalletRead:
        cached = await self._load_idempotent(actor, idempotency_key)
        if cached is not None:
            return cached

        wallet = await self._locked_wallet(actor, wallet_id)
        self._check_version(wallet, payload.expected_version)
        await self._append(
            wallet,
            WalletEventType.MONEY_WITHDRAWN,
            {
                "amount_cents": payload.amount_cents,
                "memo": payload.memo,
            },
        )
        result = WalletRead.model_validate(wallet)
        await self._store_idempotent(actor, idempotency_key, result)
        await self._session.commit()
        return result

    async def transfer(
        self,
        actor: UserRead,
        payload: TransferCreate,
        *,
        idempotency_key: str,
    ) -> TransferResult:
        cached = await self._load_idempotent_transfer(actor, idempotency_key)
        if cached is not None:
            return cached

        if payload.from_wallet_id == payload.to_wallet_id:
            raise ConflictError("Cannot transfer to the same wallet")

        source = await self._locked_wallet(actor, payload.from_wallet_id)
        dest = await self._wallets.get_for_update(payload.to_wallet_id)
        if dest is None or not self._can_view(actor, dest):
            raise NotFoundError("Wallet", payload.to_wallet_id)
        if source.currency != dest.currency:
            raise ConflictError("Currency mismatch between wallets")

        self._check_version(source, payload.expected_version)
        transfer_id = str(uuid4())
        memo = payload.memo
        amount = payload.amount_cents

        await self._append(
            source,
            WalletEventType.TRANSFER_OUT,
            {
                "amount_cents": amount,
                "memo": memo,
                "transfer_id": transfer_id,
                "counterparty_wallet_id": dest.id,
            },
        )
        await self._append(
            dest,
            WalletEventType.TRANSFER_IN,
            {
                "amount_cents": amount,
                "memo": memo,
                "transfer_id": transfer_id,
                "counterparty_wallet_id": source.id,
            },
        )
        result = TransferResult(
            from_wallet=WalletRead.model_validate(source),
            to_wallet=WalletRead.model_validate(dest),
        )
        await self._store_idempotent_transfer(actor, idempotency_key, result)
        await self._session.commit()
        return result

    async def _append(self, wallet: Wallet, event_type: WalletEventType, payload: dict) -> None:
        next_seq = wallet.version + 1
        new_balance = apply_event(
            balance_cents=wallet.balance_cents,
            event_type=event_type.value,
            payload=payload,
        )
        wallet.balance_cents = new_balance
        wallet.version = next_seq
        await self._wallets.append_event(
            WalletEvent(
                wallet_id=wallet.id,
                sequence=next_seq,
                event_type=event_type.value,
                payload=payload,
            )
        )

    async def _require_visible(self, actor: UserRead, wallet_id: str) -> Wallet:
        wallet = await self._wallets.get(wallet_id)
        if wallet is None or not self._can_view(actor, wallet):
            raise NotFoundError("Wallet", wallet_id)
        return wallet

    async def _locked_wallet(self, actor: UserRead, wallet_id: str) -> Wallet:
        wallet = await self._wallets.get_for_update(wallet_id)
        if wallet is None or not self._can_view(actor, wallet):
            raise NotFoundError("Wallet", wallet_id)
        return wallet

    @staticmethod
    def _can_view(actor: UserRead, wallet: Wallet) -> bool:
        if actor.role is UserRole.ADMIN:
            return True
        return wallet.owner_id == actor.id

    @staticmethod
    def _check_version(wallet: Wallet, expected_version: int) -> None:
        if wallet.version != expected_version:
            raise ConflictError(
                f"Stale wallet version: expected {expected_version}, current {wallet.version}"
            )

    async def _load_idempotent(self, actor: UserRead, key: str) -> WalletRead | None:
        row = await self._idempotency.get(key)
        if row is None:
            return None
        if row.user_id != actor.id:
            raise ConflictError("Idempotency key belongs to another user")
        return WalletRead.model_validate_json(row.response_json)

    async def _store_idempotent(
        self, actor: UserRead, key: str, result: WalletRead
    ) -> None:
        await self._idempotency.save(
            key=key,
            user_id=actor.id,
            response_json=result.model_dump_json(),
        )

    async def _load_idempotent_transfer(
        self, actor: UserRead, key: str
    ) -> TransferResult | None:
        row = await self._idempotency.get(key)
        if row is None:
            return None
        if row.user_id != actor.id:
            raise ConflictError("Idempotency key belongs to another user")
        return TransferResult.model_validate_json(row.response_json)

    async def _store_idempotent_transfer(
        self,
        actor: UserRead,
        key: str,
        result: TransferResult,
    ) -> None:
        await self._idempotency.save(
            key=key,
            user_id=actor.id,
            response_json=result.model_dump_json(),
        )
