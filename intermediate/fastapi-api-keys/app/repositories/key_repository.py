from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

from app.core.security import hash_api_key
from app.schemas.api_key import ApiKeyScope

# Documented in OpenAPI — for local demos and tests only.
DEMO_SEED_API_KEY = "sk_live_demo_seed_key_for_tests_only_32"


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class ApiKeyRecord:
    id: int
    owner_id: int
    name: str
    prefix: str
    secret_hash: str
    scopes: list[ApiKeyScope]
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


@dataclass
class ProjectRecord:
    id: int
    owner_id: int
    name: str
    description: str
    created_at: datetime


def _seed_keys(*, pepper: str) -> dict[int, ApiKeyRecord]:
    created = datetime.fromisoformat("2026-02-01T10:00:00+00:00")
    return {
        1: ApiKeyRecord(
            id=1,
            owner_id=2,
            name="CI read/write",
            prefix=DEMO_SEED_API_KEY[:16],
            secret_hash=hash_api_key(DEMO_SEED_API_KEY, pepper),
            scopes=[
                ApiKeyScope.PROJECTS_READ,
                ApiKeyScope.PROJECTS_WRITE,
                ApiKeyScope.METRICS_READ,
            ],
            created_at=created,
            last_used_at=None,
            revoked_at=None,
        ),
        2: ApiKeyRecord(
            id=2,
            owner_id=2,
            name="Revoked example",
            prefix="sk_live_revokedxx",
            secret_hash=hash_api_key("sk_live_revoked_key_do_not_use", pepper),
            scopes=[ApiKeyScope.METRICS_READ],
            created_at=created,
            last_used_at=None,
            revoked_at=datetime.fromisoformat("2026-02-15T12:00:00+00:00"),
        ),
    }


def _seed_projects() -> dict[int, ProjectRecord]:
    created = datetime.fromisoformat("2026-02-05T09:00:00+00:00")
    return {
        1: ProjectRecord(
            id=1,
            owner_id=2,
            name="Mobile app",
            description="Customer-facing iOS and Android clients.",
            created_at=created,
        ),
        2: ProjectRecord(
            id=2,
            owner_id=2,
            name="Internal admin",
            description="Staff tooling and dashboards.",
            created_at=created,
        ),
    }


class KeyRepository:
    def __init__(self, *, pepper: str) -> None:
        self._pepper = pepper
        self._keys = _seed_keys(pepper=pepper)
        self._projects = _seed_projects()
        self._next_key_id = max(self._keys.keys(), default=0) + 1
        self._next_project_id = max(self._projects.keys(), default=0) + 1

    @property
    def pepper(self) -> str:
        return self._pepper

    def list_keys(self) -> list[ApiKeyRecord]:
        return list(self._keys.values())

    def get_key(self, key_id: int) -> ApiKeyRecord | None:
        return self._keys.get(key_id)

    def get_key_by_hash(self, secret_hash: str) -> ApiKeyRecord | None:
        for record in self._keys.values():
            if record.secret_hash == secret_hash:
                return record
        return None

    def add_key(self, record: ApiKeyRecord) -> ApiKeyRecord:
        self._keys[record.id] = record
        return record

    def save_key(self, record: ApiKeyRecord) -> None:
        self._keys[record.id] = record

    def allocate_key_id(self) -> int:
        key_id = self._next_key_id
        self._next_key_id += 1
        return key_id

    def list_projects(self) -> list[ProjectRecord]:
        return list(self._projects.values())

    def list_projects_for_owner(self, owner_id: int) -> list[ProjectRecord]:
        return [project for project in self._projects.values() if project.owner_id == owner_id]

    def add_project(self, record: ProjectRecord) -> ProjectRecord:
        self._projects[record.id] = record
        return record

    def allocate_project_id(self) -> int:
        project_id = self._next_project_id
        self._next_project_id += 1
        return project_id

    def count_active_keys_for_owner(self, owner_id: int) -> int:
        return sum(
            1
            for key in self._keys.values()
            if key.owner_id == owner_id and key.revoked_at is None
        )


@lru_cache
def get_key_repository() -> KeyRepository:
    from app.core.config import get_settings

    settings = get_settings()
    return KeyRepository(pepper=settings.api_key_pepper)
