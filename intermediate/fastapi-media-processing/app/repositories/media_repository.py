from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from app.schemas.media import JobStatus, MediaKind, MediaOperation


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class AssetRecord:
    id: int
    owner_id: int
    filename: str
    mime_type: str
    kind: MediaKind
    size_bytes: int
    width_px: int | None
    height_px: int | None
    duration_ms: int | None
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class PresetRecord:
    id: int
    owner_id: int
    name: str
    operation: MediaOperation
    parameters: dict[str, Any]
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class JobRecord:
    id: int
    owner_id: int
    asset_id: int
    preset_id: int | None
    operation: MediaOperation
    status: JobStatus
    result_json: str | None
    error_message: str | None
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: datetime | None = None


class MediaRepository:
    def __init__(self) -> None:
        now = _utcnow()
        self._assets: dict[int, AssetRecord] = {
            1: AssetRecord(
                id=1,
                owner_id=1,
                filename="hero-banner.jpg",
                mime_type="image/jpeg",
                kind=MediaKind.IMAGE,
                size_bytes=2_480_000,
                width_px=2400,
                height_px=1600,
                duration_ms=None,
                created_at=now,
            ),
            2: AssetRecord(
                id=2,
                owner_id=2,
                filename="promo-reel.mp4",
                mime_type="video/mp4",
                kind=MediaKind.VIDEO,
                size_bytes=48_500_000,
                width_px=1920,
                height_px=1080,
                duration_ms=125_000,
                created_at=now,
            ),
        }
        self._presets: dict[int, PresetRecord] = {
            1: PresetRecord(
                id=1,
                owner_id=1,
                name="Web thumbnail",
                operation=MediaOperation.THUMBNAIL,
                parameters={"width": 320, "height": 180},
                created_at=now,
            ),
        }
        self._jobs: dict[int, JobRecord] = {
            1: JobRecord(
                id=1,
                owner_id=1,
                asset_id=1,
                preset_id=1,
                operation=MediaOperation.THUMBNAIL,
                status=JobStatus.COMPLETED,
                result_json=None,
                error_message=None,
                created_at=datetime.fromisoformat("2026-03-10T08:00:00+00:00"),
                completed_at=datetime.fromisoformat("2026-03-10T08:00:01+00:00"),
            ),
        }
        self._next_asset_id = 3
        self._next_preset_id = 2
        self._next_job_id = 2

    def list_assets_for_owner(self, owner_id: int) -> list[AssetRecord]:
        return [row for row in self._assets.values() if row.owner_id == owner_id]

    def list_all_assets(self) -> list[AssetRecord]:
        return list(self._assets.values())

    def get_asset(self, asset_id: int) -> AssetRecord | None:
        return self._assets.get(asset_id)

    def add_asset(self, record: AssetRecord) -> AssetRecord:
        self._assets[record.id] = record
        return record

    def allocate_asset_id(self) -> int:
        asset_id = self._next_asset_id
        self._next_asset_id += 1
        return asset_id

    def update_asset(self, asset_id: int, *, filename: str | None) -> AssetRecord | None:
        record = self._assets.get(asset_id)
        if record is None:
            return None
        if filename is not None:
            record.filename = filename
        return record

    def delete_asset(self, asset_id: int) -> AssetRecord | None:
        return self._assets.pop(asset_id, None)

    def list_presets_for_owner(self, owner_id: int) -> list[PresetRecord]:
        return [row for row in self._presets.values() if row.owner_id == owner_id]

    def list_all_presets(self) -> list[PresetRecord]:
        return list(self._presets.values())

    def get_preset(self, preset_id: int) -> PresetRecord | None:
        return self._presets.get(preset_id)

    def add_preset(self, record: PresetRecord) -> PresetRecord:
        self._presets[record.id] = record
        return record

    def allocate_preset_id(self) -> int:
        preset_id = self._next_preset_id
        self._next_preset_id += 1
        return preset_id

    def update_preset(
        self,
        preset_id: int,
        *,
        name: str | None,
        operation: MediaOperation | None,
        parameters: dict[str, Any] | None,
        parameters_set: bool,
    ) -> PresetRecord | None:
        record = self._presets.get(preset_id)
        if record is None:
            return None
        if name is not None:
            record.name = name
        if operation is not None:
            record.operation = operation
        if parameters_set:
            record.parameters = parameters or {}
        return record

    def delete_preset(self, preset_id: int) -> PresetRecord | None:
        return self._presets.pop(preset_id, None)

    def list_jobs_for_owner(self, owner_id: int) -> list[JobRecord]:
        rows = [row for row in self._jobs.values() if row.owner_id == owner_id]
        rows.sort(key=lambda row: row.created_at, reverse=True)
        return rows

    def get_job(self, job_id: int) -> JobRecord | None:
        return self._jobs.get(job_id)

    def add_job(self, record: JobRecord) -> JobRecord:
        self._jobs[record.id] = record
        return record

    def allocate_job_id(self) -> int:
        job_id = self._next_job_id
        self._next_job_id += 1
        return job_id


@lru_cache
def get_media_repository() -> MediaRepository:
    return MediaRepository()
