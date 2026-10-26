from datetime import UTC, datetime

from app.core.exceptions import ConflictError, NotFoundError
from app.core.webhook_tokens import generate_webhook_token, hash_webhook_token
from app.repositories.webhook_repository import EndpointRecord, WebhookRepository
from app.schemas.user import UserRead, UserRole
from app.schemas.webhook import (
    EndpointCreate,
    EndpointProvisioned,
    EndpointRead,
    EndpointStatus,
    EndpointUpdate,
)


class EndpointService:
    def __init__(self, repository: WebhookRepository) -> None:
        self._repo = repository

    def list_endpoints(self, current_user: UserRead) -> list[EndpointRead]:
        if current_user.role is UserRole.ADMIN:
            rows = self._repo.list_endpoints()
        else:
            rows = self._repo.list_endpoints_for_owner(current_user.id)
        rows.sort(key=lambda row: row.slug)
        return [self._read(row) for row in rows]

    def provision(self, current_user: UserRead, payload: EndpointCreate) -> EndpointProvisioned:
        if self._repo.slug_exists(payload.slug):
            raise ConflictError(f"Endpoint slug {payload.slug!r} already exists")
        plaintext = generate_webhook_token()
        record = EndpointRecord(
            id=self._repo.allocate_endpoint_id(),
            owner_id=current_user.id,
            slug=payload.slug,
            name=payload.name,
            description=payload.description,
            status=EndpointStatus.ACTIVE,
            token_hash=hash_webhook_token(plaintext),
            created_at=datetime.now(UTC),
        )
        self._repo.add_endpoint(record)
        base = self._read(record)
        return EndpointProvisioned(**base.model_dump(), webhook_token=plaintext)

    def get_endpoint(self, current_user: UserRead, slug: str) -> EndpointRead:
        return self._read(self._require_access(current_user, slug))

    def update_endpoint(
        self,
        current_user: UserRead,
        slug: str,
        payload: EndpointUpdate,
    ) -> EndpointRead:
        record = self._require_owner(current_user, slug)
        fields = payload.model_dump(exclude_unset=True)
        if fields.get("name") is not None:
            record.name = fields["name"]
        if fields.get("description") is not None:
            record.description = fields["description"]
        if fields.get("status") is not None:
            record.status = EndpointStatus(fields["status"])
        return self._read(record)

    def delete_endpoint(self, current_user: UserRead, slug: str) -> None:
        self._require_owner(current_user, slug)
        if self._repo.delete_endpoint(slug) is None:
            raise NotFoundError("Endpoint", slug)

    def verify_ingest_token(self, slug: str, token: str) -> EndpointRecord:
        from app.core.webhook_tokens import verify_webhook_token

        record = self._repo.get_endpoint_by_slug(slug)
        if record is None:
            raise NotFoundError("Endpoint", slug)
        if not verify_webhook_token(token, record.token_hash):
            raise NotFoundError("Endpoint", slug)
        return record

    def _require_access(self, current_user: UserRead, slug: str) -> EndpointRecord:
        record = self._repo.get_endpoint_by_slug(slug)
        if record is None:
            raise NotFoundError("Endpoint", slug)
        if current_user.role is not UserRole.ADMIN and record.owner_id != current_user.id:
            raise NotFoundError("Endpoint", slug)
        return record

    def _require_owner(self, current_user: UserRead, slug: str) -> EndpointRecord:
        record = self._require_access(current_user, slug)
        if record.owner_id != current_user.id:
            raise NotFoundError("Endpoint", slug)
        return record

    def _read(self, record: EndpointRecord) -> EndpointRead:
        return EndpointRead(
            id=record.id,
            owner_id=record.owner_id,
            slug=record.slug,
            name=record.name,
            description=record.description,
            status=record.status,
            delivery_count=self._repo.delivery_count(record.id),
            pending_count=self._repo.pending_count(record.id),
            ingest_path=f"/api/v1/hooks/{record.slug}/deliveries",
            created_at=record.created_at,
        )
