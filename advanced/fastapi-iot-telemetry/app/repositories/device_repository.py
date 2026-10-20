from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telemetry import Device


class DeviceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Device]:
        result = await self._session.scalars(select(Device).order_by(Device.key))
        return list(result)

    async def get_by_key(self, key: str) -> Device | None:
        return await self._session.scalar(select(Device).where(Device.key == key))

    async def get_by_id(self, device_id: int) -> Device | None:
        return await self._session.get(Device, device_id)

    async def add(self, device: Device) -> Device:
        self._session.add(device)
        await self._session.flush()
        return device

    async def save(self) -> None:
        await self._session.flush()
