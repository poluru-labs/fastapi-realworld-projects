from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.sync_node_repository import SyncNodeRepository
from app.repositories.sync_repository import SyncRepository
from app.schemas.editor import (
    ClaimSyncRequest,
    CompleteSyncRequest,
    SyncHeartbeat,
    SyncRead,
    SyncRegister,
    SyncStatus,
)
from app.schemas.user import UserRead, UserRole


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class SyncService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._sync = SyncRepository(session)
        self._nodes = SyncNodeRepository(session)

    async def register_node(self, actor: UserRead, payload: SyncRegister) -> dict[str, str]:
        now = datetime.now(UTC)
        await self._nodes.upsert(
            node_id=payload.node_id,
            registered_by_id=actor.id,
            document_slugs=payload.document_slugs,
            now=now,
        )
        await self._session.commit()
        return {"node_id": payload.node_id, "status": "registered"}

    async def heartbeat(self, actor: UserRead, payload: SyncHeartbeat) -> dict[str, str]:
        node = await self._nodes.get(payload.node_id)
        if node is None:
            raise NotFoundError("SyncNode", payload.node_id)
        if actor.role is not UserRole.ADMIN and node.registered_by_id != actor.id:
            raise ForbiddenError("You can only heartbeat nodes you registered")
        await self._nodes.heartbeat(payload.node_id, datetime.now(UTC))
        await self._session.commit()
        return {"node_id": payload.node_id, "status": "ok"}

    async def claim(self, actor: UserRead, payload: ClaimSyncRequest) -> SyncRead:
        node = await self._nodes.get(payload.node_id)
        if node is None:
            raise NotFoundError("SyncNode", payload.node_id)
        if actor.role is not UserRole.ADMIN and node.registered_by_id != actor.id:
            raise ForbiddenError("You can only claim with nodes you registered")

        now = datetime.now(UTC)
        row = await self._sync.find_claimable(document_slugs=list(node.document_slugs), now=now)
        if row is None:
            raise NotFoundError("ClaimableSync", "none")

        lease = timedelta(seconds=self._settings.sync_lease_seconds)
        row.status = SyncStatus.SYNCING.value
        row.lease_holder = payload.node_id
        row.lease_expires_at = now + lease
        row.version += 1
        await self._sync.save()
        await self._session.commit()
        return SyncRead.model_validate(row)

    async def complete(
        self,
        actor: UserRead,
        sync_id: int,
        payload: CompleteSyncRequest,
    ) -> SyncRead:
        row = await self._sync.get(sync_id)
        if row is None:
            raise NotFoundError("SyncOutbox", sync_id)
        node = await self._nodes.get(payload.node_id)
        if node is None:
            raise NotFoundError("SyncNode", payload.node_id)
        if actor.role is not UserRole.ADMIN and node.registered_by_id != actor.id:
            raise ForbiddenError("You can only complete sync jobs with nodes you registered")

        if row.status != SyncStatus.SYNCING.value:
            raise ConflictError("Sync job is not in syncing state")
        if row.lease_holder != payload.node_id:
            raise ForbiddenError("This node does not hold the lease for this sync job")
        now = datetime.now(UTC)
        lease_expires = _as_utc(row.lease_expires_at)
        if lease_expires is not None and lease_expires < now:
            raise ConflictError("Lease expired; sync job may be reclaimed")
        if row.version != payload.expected_version:
            raise ConflictError(
                f"Stale version: expected {payload.expected_version}, current is {row.version}"
            )

        row.status = SyncStatus.SYNCED.value
        row.synced_at = now
        row.lease_holder = None
        row.lease_expires_at = None
        row.version += 1
        await self._sync.save()
        await self._session.commit()
        return SyncRead.model_validate(row)
