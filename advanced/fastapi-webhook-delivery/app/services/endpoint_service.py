"""Webhook endpoint subscriptions (URL, secret, filters)."""

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.webhook import WebhookEndpoint
from app.repositories.webhook_repository import WebhookEndpointRepository
from app.schemas.user import UserRead, UserRole
from app.schemas.webhook import (
    WebhookEndpointCreate,
    WebhookEndpointCreated,
    WebhookEndpointRead,
    WebhookEndpointUpdate,
)


class EndpointService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._endpoints = WebhookEndpointRepository(session)

    async def list_endpoints(self, actor: UserRead) -> list[WebhookEndpointRead]:
        rows = await self._endpoints.list_for_owner(actor.id)
        return [self._to_read(row) for row in rows]

    async def get_endpoint(self, actor: UserRead, endpoint_id: int) -> WebhookEndpointRead:
        row = await self._require_visible(actor, endpoint_id)
        return self._to_read(row)

    async def create_endpoint(
        self,
        actor: UserRead,
        payload: WebhookEndpointCreate,
    ) -> WebhookEndpointCreated:
        signing_secret = secrets.token_urlsafe(32)
        row = WebhookEndpoint(
            owner_id=actor.id,
            url=str(payload.url),
            description=payload.description,
            signing_secret=signing_secret,
            secret_prefix=signing_secret[:8],
            event_types=payload.event_types,
            enabled=payload.enabled,
        )
        await self._endpoints.add(row)
        await self._session.commit()
        base = self._to_read(row)
        return WebhookEndpointCreated(**base.model_dump(), signing_secret=signing_secret)

    async def update_endpoint(
        self,
        actor: UserRead,
        endpoint_id: int,
        payload: WebhookEndpointUpdate,
    ) -> WebhookEndpointRead:
        row = await self._require_visible(actor, endpoint_id)
        changes = payload.model_dump(exclude_unset=True)
        if "url" in changes and changes["url"] is not None:
            row.url = str(changes["url"])
        if "description" in changes:
            row.description = changes["description"] or ""
        if "event_types" in changes and changes["event_types"] is not None:
            row.event_types = changes["event_types"] or ["*"]
        if "enabled" in changes and changes["enabled"] is not None:
            row.enabled = changes["enabled"]
        await self._session.commit()
        return self._to_read(row)

    async def _require_visible(self, actor: UserRead, endpoint_id: int) -> WebhookEndpoint:
        row = await self._endpoints.get(endpoint_id)
        if row is None or not self._can_view(actor, row):
            raise NotFoundError("WebhookEndpoint", endpoint_id)
        return row

    @staticmethod
    def _can_view(actor: UserRead, row: WebhookEndpoint) -> bool:
        if actor.role is UserRole.ADMIN:
            return True
        return row.owner_id == actor.id

    @staticmethod
    def _to_read(row: WebhookEndpoint) -> WebhookEndpointRead:
        return WebhookEndpointRead(
            id=row.id,
            url=row.url,
            description=row.description,
            event_types=list(row.event_types),
            enabled=row.enabled,
            secret_prefix=row.secret_prefix,
            created_at=row.created_at,
        )
