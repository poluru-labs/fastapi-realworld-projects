from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import WebhookDelivery, WebhookEndpoint, WebhookEvent


class WebhookEndpointRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, endpoint_id: int) -> WebhookEndpoint | None:
        return await self._session.get(WebhookEndpoint, endpoint_id)

    async def list_for_owner(self, owner_id: int) -> list[WebhookEndpoint]:
        stmt = (
            select(WebhookEndpoint)
            .where(WebhookEndpoint.owner_id == owner_id)
            .order_by(WebhookEndpoint.id.desc())
        )
        return list(await self._session.scalars(stmt))

    async def list_enabled_for_owner(self, owner_id: int) -> list[WebhookEndpoint]:
        stmt = select(WebhookEndpoint).where(
            WebhookEndpoint.owner_id == owner_id,
            WebhookEndpoint.enabled.is_(True),
        )
        return list(await self._session.scalars(stmt))

    async def add(self, row: WebhookEndpoint) -> WebhookEndpoint:
        self._session.add(row)
        await self._session.flush()
        return row


class WebhookEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, event_id: int) -> WebhookEvent | None:
        return await self._session.get(WebhookEvent, event_id)

    async def get_by_idempotency(self, owner_id: int, key: str) -> WebhookEvent | None:
        stmt = select(WebhookEvent).where(
            WebhookEvent.owner_id == owner_id,
            WebhookEvent.idempotency_key == key,
        )
        return await self._session.scalar(stmt)

    async def list_for_owner(self, owner_id: int) -> list[WebhookEvent]:
        stmt = (
            select(WebhookEvent)
            .where(WebhookEvent.owner_id == owner_id)
            .order_by(WebhookEvent.id.desc())
        )
        return list(await self._session.scalars(stmt))

    async def add(self, row: WebhookEvent) -> WebhookEvent:
        self._session.add(row)
        await self._session.flush()
        return row


class WebhookDeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, delivery_id: int) -> WebhookDelivery | None:
        return await self._session.get(WebhookDelivery, delivery_id)

    async def list_for_event(self, event_id: int) -> list[WebhookDelivery]:
        stmt = (
            select(WebhookDelivery)
            .where(WebhookDelivery.event_id == event_id)
            .order_by(WebhookDelivery.endpoint_id, WebhookDelivery.attempt_number)
        )
        return list(await self._session.scalars(stmt))

    async def latest_for_event_endpoint(
        self, event_id: int, endpoint_id: int
    ) -> WebhookDelivery | None:
        stmt = (
            select(WebhookDelivery)
            .where(
                WebhookDelivery.event_id == event_id,
                WebhookDelivery.endpoint_id == endpoint_id,
            )
            .order_by(WebhookDelivery.attempt_number.desc())
            .limit(1)
        )
        return await self._session.scalar(stmt)

    async def add(self, row: WebhookDelivery) -> WebhookDelivery:
        self._session.add(row)
        await self._session.flush()
        return row
