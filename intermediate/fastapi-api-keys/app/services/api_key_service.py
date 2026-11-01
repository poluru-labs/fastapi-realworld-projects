from datetime import UTC, datetime

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import api_key_prefix, generate_api_key, hash_api_key
from app.repositories.key_repository import ApiKeyRecord, KeyRepository
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyRead, ApiKeyUpdate
from app.schemas.user import UserRead, UserRole


class ApiKeyService:
    def __init__(self, repository: KeyRepository, settings: Settings) -> None:
        self._repo = repository
        self._settings = settings

    def list_keys(self, actor: UserRead) -> list[ApiKeyRead]:
        rows = self._repo.list_keys()
        if actor.role is not UserRole.ADMIN:
            rows = [row for row in rows if row.owner_id == actor.id]
        rows.sort(key=lambda row: row.created_at, reverse=True)
        return [self._read(row) for row in rows]

    def get_key(self, actor: UserRead, key_id: int) -> ApiKeyRead:
        return self._read(self._visible_key(actor, key_id))

    def create_key(self, actor: UserRead, payload: ApiKeyCreate) -> ApiKeyCreated:
        secret = generate_api_key()
        now = datetime.now(UTC)
        record = ApiKeyRecord(
            id=self._repo.allocate_key_id(),
            owner_id=actor.id,
            name=payload.name,
            prefix=api_key_prefix(secret),
            secret_hash=hash_api_key(secret, self._settings.api_key_pepper),
            scopes=list(payload.scopes),
            created_at=now,
            last_used_at=None,
            revoked_at=None,
        )
        self._repo.add_key(record)
        return ApiKeyCreated(key=self._read(record), secret=secret)

    def update_key(self, actor: UserRead, key_id: int, payload: ApiKeyUpdate) -> ApiKeyRead:
        record = self._owned_key(actor, key_id)
        if record.revoked_at is not None:
            raise ConflictError("Revoked API keys cannot be updated")
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is not None:
            record.name = changes["name"]
        if "scopes" in changes and changes["scopes"] is not None:
            record.scopes = list(changes["scopes"])
        self._repo.save_key(record)
        return self._read(record)

    def revoke_key(self, actor: UserRead, key_id: int) -> ApiKeyRead:
        record = self._owned_key(actor, key_id)
        if record.revoked_at is not None:
            raise ConflictError("API key is already revoked")
        record.revoked_at = datetime.now(UTC)
        self._repo.save_key(record)
        return self._read(record)

    def rotate_key(self, actor: UserRead, key_id: int) -> ApiKeyCreated:
        record = self._owned_key(actor, key_id)
        if record.revoked_at is not None:
            raise ConflictError("Cannot rotate a revoked API key")
        record.revoked_at = datetime.now(UTC)
        self._repo.save_key(record)
        return self.create_key(
            actor,
            ApiKeyCreate(name=f"{record.name} (rotated)", scopes=record.scopes),
        )

    def _visible_key(self, actor: UserRead, key_id: int) -> ApiKeyRecord:
        record = self._repo.get_key(key_id)
        if record is None or (record.owner_id != actor.id and actor.role is not UserRole.ADMIN):
            raise NotFoundError("API key", key_id)
        return record

    def _owned_key(self, actor: UserRead, key_id: int) -> ApiKeyRecord:
        record = self._repo.get_key(key_id)
        if record is None or record.owner_id != actor.id:
            raise NotFoundError("API key", key_id)
        return record

    @staticmethod
    def _read(record: ApiKeyRecord) -> ApiKeyRead:
        return ApiKeyRead(
            id=record.id,
            name=record.name,
            prefix=record.prefix,
            scopes=record.scopes,
            owner_id=record.owner_id,
            created_at=record.created_at,
            last_used_at=record.last_used_at,
            revoked_at=record.revoked_at,
        )
