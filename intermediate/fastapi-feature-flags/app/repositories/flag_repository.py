from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

from app.schemas.flag import FlagEnvironment

RUNTIME_TOKEN_DEMO = "seed-runtime-token-demo"


@dataclass
class FlagRecord:
    id: int
    key: str
    name: str
    description: str
    environment: FlagEnvironment
    enabled: bool
    rollout_percentage: int
    allowlist_user_ids: list[str]
    owner_id: int
    created_at: datetime
    updated_at: datetime


@dataclass
class RuntimeTokenRecord:
    token: str
    owner_id: int
    label: str


def _seed() -> tuple[dict[int, FlagRecord], list[RuntimeTokenRecord]]:
    created = datetime.fromisoformat("2026-02-01T10:00:00+00:00")
    flags = {
        1: FlagRecord(
            id=1,
            key="new-checkout",
            name="New checkout flow",
            description="Roll out redesigned checkout to a percentage of users.",
            environment=FlagEnvironment.PRODUCTION,
            enabled=True,
            rollout_percentage=50,
            allowlist_user_ids=["u_vip_1"],
            owner_id=2,
            created_at=created,
            updated_at=created,
        ),
        2: FlagRecord(
            id=2,
            key="dark-mode",
            name="Dark mode",
            description="UI theme toggle for all signed-in users.",
            environment=FlagEnvironment.PRODUCTION,
            enabled=True,
            rollout_percentage=100,
            allowlist_user_ids=[],
            owner_id=2,
            created_at=created,
            updated_at=created,
        ),
        3: FlagRecord(
            id=3,
            key="beta-api",
            name="Beta API surface",
            description="Master kill switch — currently off.",
            environment=FlagEnvironment.STAGING,
            enabled=False,
            rollout_percentage=100,
            allowlist_user_ids=["u_internal_qa"],
            owner_id=2,
            created_at=created,
            updated_at=created,
        ),
    }
    tokens = [
        RuntimeTokenRecord(
            token=RUNTIME_TOKEN_DEMO,
            owner_id=2,
            label="Demo mobile app",
        ),
    ]
    return flags, tokens


class FlagRepository:
    def __init__(self) -> None:
        flags, tokens = _seed()
        self._flags = flags
        self._tokens = {record.token: record for record in tokens}
        self._next_id = max(self._flags.keys(), default=0) + 1

    def list_flags(self) -> list[FlagRecord]:
        return list(self._flags.values())

    def get_flag(self, flag_id: int) -> FlagRecord | None:
        return self._flags.get(flag_id)

    def get_flag_by_key(self, key: str) -> FlagRecord | None:
        for record in self._flags.values():
            if record.key == key:
                return record
        return None

    def key_taken(self, key: str) -> bool:
        return self.get_flag_by_key(key) is not None

    def add_flag(self, record: FlagRecord) -> FlagRecord:
        self._flags[record.id] = record
        return record

    def save_flag(self, record: FlagRecord) -> None:
        self._flags[record.id] = record

    def delete_flag(self, flag_id: int) -> None:
        self._flags.pop(flag_id, None)

    def allocate_id(self) -> int:
        flag_id = self._next_id
        self._next_id += 1
        return flag_id

    def resolve_runtime_token(self, token: str) -> RuntimeTokenRecord | None:
        return self._tokens.get(token)


@lru_cache
def get_flag_repository() -> FlagRepository:
    return FlagRepository()
