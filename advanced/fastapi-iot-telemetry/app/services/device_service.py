from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.device_tokens import generate_device_token, hash_device_token
from app.core.exceptions import ConflictError, NotFoundError
from app.models.telemetry import Device
from app.repositories.device_repository import DeviceRepository
from app.schemas.telemetry import (
    DeviceCreate,
    DeviceProvisioned,
    DeviceRead,
    DeviceStatus,
    DeviceUpdate,
)


class DeviceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._devices = DeviceRepository(session)

    async def list_devices(self) -> list[DeviceRead]:
        rows = await self._devices.list_all()
        return [DeviceRead.model_validate(row) for row in rows]

    async def get_device(self, key: str) -> DeviceRead:
        row = await self._require_device(key)
        return DeviceRead.model_validate(row)

    async def provision(self, payload: DeviceCreate) -> DeviceProvisioned:
        if await self._devices.get_by_key(payload.key) is not None:
            raise ConflictError("Another device already uses this key")
        token = generate_device_token()
        now = datetime.now(UTC)
        device = Device(
            key=payload.key,
            name=payload.name,
            site=payload.site,
            status=DeviceStatus.ACTIVE.value,
            ingest_token_hash=hash_device_token(token),
            last_seen_at=None,
            created_at=now,
            updated_at=now,
        )
        await self._devices.add(device)
        await self._session.commit()
        body = DeviceRead.model_validate(device)
        return DeviceProvisioned(**body.model_dump(), ingest_token=token)

    async def update_device(self, key: str, payload: DeviceUpdate) -> DeviceRead:
        device = await self._require_device(key)
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is not None:
            device.name = changes["name"]
        if "site" in changes and changes["site"] is not None:
            device.site = changes["site"]
        device.updated_at = datetime.now(UTC)
        await self._devices.save()
        await self._session.commit()
        return DeviceRead.model_validate(device)

    async def suspend(self, key: str) -> DeviceRead:
        device = await self._require_device(key)
        if device.status == DeviceStatus.SUSPENDED.value:
            raise ConflictError("Device is already suspended")
        device.status = DeviceStatus.SUSPENDED.value
        device.updated_at = datetime.now(UTC)
        await self._devices.save()
        await self._session.commit()
        return DeviceRead.model_validate(device)

    async def resume(self, key: str) -> DeviceRead:
        device = await self._require_device(key)
        if device.status == DeviceStatus.DECOMMISSIONED.value:
            raise ConflictError("Decommissioned devices cannot resume")
        if device.status == DeviceStatus.ACTIVE.value:
            raise ConflictError("Device is already active")
        device.status = DeviceStatus.ACTIVE.value
        device.updated_at = datetime.now(UTC)
        await self._devices.save()
        await self._session.commit()
        return DeviceRead.model_validate(device)

    async def decommission(self, key: str) -> DeviceRead:
        device = await self._require_device(key)
        if device.status == DeviceStatus.DECOMMISSIONED.value:
            raise ConflictError("Device is already decommissioned")
        device.status = DeviceStatus.DECOMMISSIONED.value
        device.updated_at = datetime.now(UTC)
        await self._devices.save()
        await self._session.commit()
        return DeviceRead.model_validate(device)

    async def require_active_device(self, key: str) -> Device:
        device = await self._require_device(key)
        if device.status != DeviceStatus.ACTIVE.value:
            raise ConflictError("Device is not accepting telemetry")
        return device

    async def verify_ingest_token(self, key: str, token: str) -> Device:
        device = await self.require_active_device(key)
        from app.core.device_tokens import verify_device_token

        if not verify_device_token(token, device.ingest_token_hash):
            from app.core.exceptions import UnauthorizedError

            raise UnauthorizedError("Invalid device ingest token")
        return device

    async def touch_last_seen(self, device: Device, when: datetime) -> None:
        device.last_seen_at = when
        device.updated_at = when
        await self._devices.save()

    async def _require_device(self, key: str) -> Device:
        device = await self._devices.get_by_key(key)
        if device is None:
            raise NotFoundError("Device", key)
        return device
