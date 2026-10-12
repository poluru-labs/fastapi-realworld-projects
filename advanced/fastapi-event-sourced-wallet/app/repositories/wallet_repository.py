from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet import Wallet, WalletEvent


class WalletRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, wallet_id: str) -> Wallet | None:
        return await self._session.get(Wallet, wallet_id)

    async def get_for_update(self, wallet_id: str) -> Wallet | None:
        stmt = select(Wallet).where(Wallet.id == wallet_id).with_for_update()
        return await self._session.scalar(stmt)

    async def list_for_owner(self, owner_id: int) -> list[Wallet]:
        stmt = select(Wallet).where(Wallet.owner_id == owner_id).order_by(Wallet.created_at)
        result = await self._session.scalars(stmt)
        return list(result.all())

    async def list_all(self) -> list[Wallet]:
        stmt = select(Wallet).order_by(Wallet.created_at)
        result = await self._session.scalars(stmt)
        return list(result.all())

    async def add(self, wallet: Wallet) -> Wallet:
        self._session.add(wallet)
        await self._session.flush()
        return wallet

    async def append_event(self, event: WalletEvent) -> WalletEvent:
        self._session.add(event)
        await self._session.flush()
        return event

    async def list_events(self, wallet_id: str) -> list[WalletEvent]:
        stmt = (
            select(WalletEvent)
            .where(WalletEvent.wallet_id == wallet_id)
            .order_by(WalletEvent.sequence)
        )
        result = await self._session.scalars(stmt)
        return list(result.all())
