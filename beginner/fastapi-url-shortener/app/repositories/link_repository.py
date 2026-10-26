from __future__ import annotations

import secrets
import string
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


_CODE_ALPHABET = string.ascii_letters + string.digits


@dataclass
class LinkRecord:
    id: int
    code: str
    target_url: str
    title: str
    click_count: int
    is_active: bool
    created_at: datetime = field(default_factory=_utcnow)


def _seed() -> dict[str, LinkRecord]:
    return {
        "docs": LinkRecord(
            id=1,
            code="docs",
            target_url="https://fastapi.tiangolo.com",
            title="FastAPI docs",
            click_count=12,
            is_active=True,
            created_at=datetime.fromisoformat("2026-01-10T09:00:00+00:00"),
        ),
        "github": LinkRecord(
            id=2,
            code="github",
            target_url="https://github.com/tiangolo/fastapi",
            title="FastAPI on GitHub",
            click_count=4,
            is_active=True,
            created_at=datetime.fromisoformat("2026-02-01T14:30:00+00:00"),
        ),
        "old-sale": LinkRecord(
            id=3,
            code="old-sale",
            target_url="https://example.com/promo",
            title="Expired promotion",
            click_count=99,
            is_active=False,
            created_at=datetime.fromisoformat("2025-12-01T08:00:00+00:00"),
        ),
    }


class LinkRepository:
    """In-memory short links."""

    def __init__(self) -> None:
        self._by_code = _seed()
        self._next_id = max((link.id for link in self._by_code.values()), default=0) + 1

    def list_links(self) -> list[LinkRecord]:
        return list(self._by_code.values())

    def get_by_code(self, code: str) -> LinkRecord | None:
        return self._by_code.get(code)

    def code_exists(self, code: str) -> bool:
        return code in self._by_code

    def create_link(
        self,
        *,
        code: str,
        target_url: str,
        title: str,
    ) -> LinkRecord:
        link_id = self._next_id
        self._next_id += 1
        record = LinkRecord(
            id=link_id,
            code=code,
            target_url=target_url,
            title=title,
            click_count=0,
            is_active=True,
        )
        self._by_code[code] = record
        return record

    def update_link(
        self,
        code: str,
        *,
        target_url: str | None,
        title: str | None,
        is_active: bool | None,
    ) -> LinkRecord | None:
        record = self._by_code.get(code)
        if record is None:
            return None
        if target_url is not None:
            record.target_url = target_url
        if title is not None:
            record.title = title
        if is_active is not None:
            record.is_active = is_active
        return record

    def delete_link(self, code: str) -> LinkRecord | None:
        return self._by_code.pop(code, None)

    def record_click(self, code: str) -> LinkRecord | None:
        record = self._by_code.get(code)
        if record is None:
            return None
        record.click_count += 1
        return record

    @staticmethod
    def generate_code(length: int = 7) -> str:
        return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))


@lru_cache
def get_link_repository() -> LinkRepository:
    return LinkRepository()
