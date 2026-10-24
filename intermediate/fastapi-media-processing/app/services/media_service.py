from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.repositories.media_repository import AssetRecord, JobRecord, MediaRepository, PresetRecord
from app.schemas.media import (
    AssetCreate,
    AssetRead,
    AssetUpdate,
    JobOutput,
    JobRead,
    JobResult,
    JobStatus,
    JobSubmit,
    MediaKind,
    MediaOperation,
    OperationCatalogEntry,
    PresetCreate,
    PresetRead,
    PresetUpdate,
)
from app.schemas.user import UserRead, UserRole

_OPERATION_KINDS: dict[MediaOperation, set[MediaKind]] = {
    MediaOperation.THUMBNAIL: {MediaKind.IMAGE},
    MediaOperation.RESIZE: {MediaKind.IMAGE, MediaKind.VIDEO},
    MediaOperation.TRANSCODE: {MediaKind.VIDEO},
    MediaOperation.EXTRACT_AUDIO: {MediaKind.VIDEO},
}

_CATALOG: list[OperationCatalogEntry] = [
    OperationCatalogEntry(
        operation=MediaOperation.THUMBNAIL,
        description="Generate a fixed-size JPEG preview.",
        allowed_kinds=[MediaKind.IMAGE],
        parameter_schema={
            "width": {"type": "integer", "minimum": 16, "maximum": 4096},
            "height": {"type": "integer", "minimum": 16, "maximum": 4096},
        },
    ),
    OperationCatalogEntry(
        operation=MediaOperation.RESIZE,
        description="Fit inside a bounding box while preserving aspect ratio.",
        allowed_kinds=[MediaKind.IMAGE, MediaKind.VIDEO],
        parameter_schema={
            "max_width": {"type": "integer", "minimum": 16, "maximum": 8192},
            "max_height": {"type": "integer", "minimum": 16, "maximum": 8192},
        },
    ),
    OperationCatalogEntry(
        operation=MediaOperation.TRANSCODE,
        description="Simulated video re-encode to another container.",
        allowed_kinds=[MediaKind.VIDEO],
        parameter_schema={"format": {"type": "string", "enum": ["mp4", "webm"]}},
    ),
    OperationCatalogEntry(
        operation=MediaOperation.EXTRACT_AUDIO,
        description="Simulated audio track export from video.",
        allowed_kinds=[MediaKind.VIDEO],
        parameter_schema={"format": {"type": "string", "enum": ["mp3", "wav"]}},
    ),
]


class MediaService:
    def __init__(self, repository: MediaRepository) -> None:
        self._repo = repository
        self._ensure_seed_job_result()

    def list_assets(self, current_user: UserRead) -> list[AssetRead]:
        if current_user.role is UserRole.ADMIN:
            rows = self._repo.list_all_assets()
        else:
            rows = self._repo.list_assets_for_owner(current_user.id)
        rows.sort(key=lambda row: (row.filename.casefold(), row.id))
        return [self._asset_read(row) for row in rows]

    def create_asset(self, current_user: UserRead, payload: AssetCreate) -> AssetRead:
        record = AssetRecord(
            id=self._repo.allocate_asset_id(),
            owner_id=current_user.id,
            filename=payload.filename,
            mime_type=payload.mime_type,
            kind=payload.kind,
            size_bytes=payload.size_bytes,
            width_px=payload.width_px,
            height_px=payload.height_px,
            duration_ms=payload.duration_ms,
            created_at=datetime.now(UTC),
        )
        self._repo.add_asset(record)
        return self._asset_read(record)

    def get_asset(self, current_user: UserRead, asset_id: int) -> AssetRead:
        return self._asset_read(self._require_asset_access(current_user, asset_id))

    def update_asset(
        self,
        current_user: UserRead,
        asset_id: int,
        payload: AssetUpdate,
    ) -> AssetRead:
        self._require_asset_owner(current_user, asset_id)
        fields = payload.model_dump(exclude_unset=True)
        record = self._repo.update_asset(asset_id, filename=fields.get("filename"))
        if record is None:
            raise NotFoundError("Asset", asset_id)
        return self._asset_read(record)

    def delete_asset(self, current_user: UserRead, asset_id: int) -> None:
        self._require_asset_owner(current_user, asset_id)
        if self._repo.delete_asset(asset_id) is None:
            raise NotFoundError("Asset", asset_id)

    def list_presets(self, current_user: UserRead) -> list[PresetRead]:
        if current_user.role is UserRole.ADMIN:
            rows = self._repo.list_all_presets()
        else:
            rows = self._repo.list_presets_for_owner(current_user.id)
        rows.sort(key=lambda row: (row.name.casefold(), row.id))
        return [self._preset_read(row) for row in rows]

    def create_preset(self, current_user: UserRead, payload: PresetCreate) -> PresetRead:
        self._validate_parameters(payload.operation, payload.parameters)
        record = PresetRecord(
            id=self._repo.allocate_preset_id(),
            owner_id=current_user.id,
            name=payload.name,
            operation=payload.operation,
            parameters=dict(payload.parameters),
            created_at=datetime.now(UTC),
        )
        self._repo.add_preset(record)
        return self._preset_read(record)

    def get_preset(self, current_user: UserRead, preset_id: int) -> PresetRead:
        return self._preset_read(self._require_preset_access(current_user, preset_id))

    def update_preset(
        self,
        current_user: UserRead,
        preset_id: int,
        payload: PresetUpdate,
    ) -> PresetRead:
        record = self._require_preset_owner(current_user, preset_id)
        fields = payload.model_dump(exclude_unset=True)
        parameters_set = "parameters" in fields
        operation = fields.get("operation", record.operation)
        parameters = fields.get("parameters", record.parameters)
        if parameters_set or "operation" in fields:
            self._validate_parameters(operation, parameters)
        updated = self._repo.update_preset(
            preset_id,
            name=fields.get("name"),
            operation=fields.get("operation"),
            parameters=parameters if parameters_set else None,
            parameters_set=parameters_set,
        )
        if updated is None:
            raise NotFoundError("Preset", preset_id)
        return self._preset_read(updated)

    def delete_preset(self, current_user: UserRead, preset_id: int) -> None:
        self._require_preset_owner(current_user, preset_id)
        if self._repo.delete_preset(preset_id) is None:
            raise NotFoundError("Preset", preset_id)

    def list_operations(self, current_user: UserRead) -> list[OperationCatalogEntry]:
        if current_user.role is not UserRole.ADMIN:
            raise ForbiddenError("Operations catalog requires admin role")
        return list(_CATALOG)

    def list_jobs(self, current_user: UserRead) -> list[JobRead]:
        return [self._job_read(row) for row in self._repo.list_jobs_for_owner(current_user.id)]

    def submit_job(self, current_user: UserRead, payload: JobSubmit) -> JobRead:
        asset = self._require_asset_access(current_user, payload.asset_id)
        if asset.owner_id != current_user.id:
            raise NotFoundError("Asset", payload.asset_id)

        preset_id: int | None = None
        preset_name: str | None = None
        if payload.preset_id is not None:
            preset = self._require_preset_access(current_user, payload.preset_id)
            if preset.owner_id != current_user.id:
                raise NotFoundError("Preset", payload.preset_id)
            operation = preset.operation
            parameters = dict(preset.parameters)
            preset_id = preset.id
            preset_name = preset.name
        else:
            operation = payload.operation
            assert operation is not None
            parameters = dict(payload.parameters or {})

        self._validate_parameters(operation, parameters)
        self._ensure_operation_allowed(operation, asset.kind)

        job = JobRecord(
            id=self._repo.allocate_job_id(),
            owner_id=current_user.id,
            asset_id=asset.id,
            preset_id=preset_id,
            operation=operation,
            status=JobStatus.COMPLETED,
            result_json=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None,
        )
        try:
            result = self._build_result(
                operation=operation,
                asset=asset,
                parameters=parameters,
                preset_id=preset_id,
                job_id=job.id,
            )
            job.result_json = result.model_dump_json()
            job.completed_at = datetime.now(UTC)
        except ConflictError as exc:
            job.status = JobStatus.FAILED
            job.error_message = exc.message
            job.completed_at = datetime.now(UTC)

        self._repo.add_job(job)
        return self._job_read(job, preset_name=preset_name)

    def get_job(self, current_user: UserRead, job_id: int) -> JobRead:
        job = self._require_job_owner(current_user, job_id)
        return self._job_read(job)

    def _build_result(
        self,
        *,
        operation: MediaOperation,
        asset: AssetRecord,
        parameters: dict[str, Any],
        preset_id: int | None,
        job_id: int,
    ) -> JobResult:
        owner_id = asset.owner_id
        if operation is MediaOperation.THUMBNAIL:
            width = int(parameters["width"])
            height = int(parameters["height"])
            output = JobOutput(
                output_uri=f"processed://{owner_id}/{job_id}/thumb.jpg",
                mime_type="image/jpeg",
                size_bytes=max(32_000, asset.size_bytes // 20),
                width_px=width,
                height_px=height,
            )
            notes = f"Thumbnail at {width}x{height} from {asset.filename}"
        elif operation is MediaOperation.RESIZE:
            max_w = int(parameters["max_width"])
            max_h = int(parameters["max_height"])
            width = min(asset.width_px or max_w, max_w)
            height = min(asset.height_px or max_h, max_h)
            mime = asset.mime_type if asset.kind is MediaKind.VIDEO else "image/jpeg"
            output = JobOutput(
                output_uri=f"processed://{owner_id}/{job_id}/resized",
                mime_type=mime,
                size_bytes=max(64_000, asset.size_bytes // 3),
                width_px=width,
                height_px=height,
            )
            notes = f"Resized to fit within {max_w}x{max_h}"
        elif operation is MediaOperation.TRANSCODE:
            fmt = str(parameters["format"])
            output = JobOutput(
                output_uri=f"processed://{owner_id}/{job_id}/video.{fmt}",
                mime_type=f"video/{fmt}",
                size_bytes=max(1_000_000, asset.size_bytes // 2),
                width_px=asset.width_px,
                height_px=asset.height_px,
                duration_ms=asset.duration_ms,
            )
            notes = f"Transcoded to {fmt.upper()}"
        else:
            fmt = str(parameters["format"])
            mime = "audio/mpeg" if fmt == "mp3" else "audio/wav"
            output = JobOutput(
                output_uri=f"processed://{owner_id}/{job_id}/audio.{fmt}",
                mime_type=mime,
                size_bytes=max(500_000, (asset.duration_ms or 60_000) * 8),
                duration_ms=asset.duration_ms,
            )
            notes = f"Extracted {fmt.upper()} audio track"

        return JobResult(
            operation=operation,
            source_asset_id=asset.id,
            preset_id=preset_id,
            output=output,
            notes=notes,
        )

    def _validate_parameters(self, operation: MediaOperation, parameters: dict[str, Any]) -> None:
        if operation is MediaOperation.THUMBNAIL:
            for key in ("width", "height"):
                if key not in parameters:
                    raise ConflictError(f"Missing parameter: {key}")
        elif operation is MediaOperation.RESIZE:
            for key in ("max_width", "max_height"):
                if key not in parameters:
                    raise ConflictError(f"Missing parameter: {key}")
        elif operation in {MediaOperation.TRANSCODE, MediaOperation.EXTRACT_AUDIO}:
            fmt = parameters.get("format")
            allowed = {"mp4", "webm"} if operation is MediaOperation.TRANSCODE else {"mp3", "wav"}
            if fmt not in allowed:
                raise ConflictError(f"format must be one of: {', '.join(sorted(allowed))}")

    def _ensure_operation_allowed(self, operation: MediaOperation, kind: MediaKind) -> None:
        if kind not in _OPERATION_KINDS[operation]:
            raise ConflictError(
                f"Operation {operation.value} is not allowed for {kind.value} assets"
            )

    def _require_asset_access(self, current_user: UserRead, asset_id: int) -> AssetRecord:
        record = self._repo.get_asset(asset_id)
        if record is None:
            raise NotFoundError("Asset", asset_id)
        if current_user.role is not UserRole.ADMIN and record.owner_id != current_user.id:
            raise NotFoundError("Asset", asset_id)
        return record

    def _require_asset_owner(self, current_user: UserRead, asset_id: int) -> AssetRecord:
        record = self._require_asset_access(current_user, asset_id)
        if record.owner_id != current_user.id:
            raise NotFoundError("Asset", asset_id)
        return record

    def _require_preset_access(self, current_user: UserRead, preset_id: int) -> PresetRecord:
        record = self._repo.get_preset(preset_id)
        if record is None:
            raise NotFoundError("Preset", preset_id)
        if current_user.role is not UserRole.ADMIN and record.owner_id != current_user.id:
            raise NotFoundError("Preset", preset_id)
        return record

    def _require_preset_owner(self, current_user: UserRead, preset_id: int) -> PresetRecord:
        record = self._require_preset_access(current_user, preset_id)
        if record.owner_id != current_user.id:
            raise NotFoundError("Preset", preset_id)
        return record

    def _require_job_owner(self, current_user: UserRead, job_id: int) -> JobRecord:
        job = self._repo.get_job(job_id)
        if job is None or job.owner_id != current_user.id:
            raise NotFoundError("Processing job", job_id)
        return job

    def _ensure_seed_job_result(self) -> None:
        seed = self._repo.get_job(1)
        if seed is None or seed.result_json is not None:
            return
        asset = self._repo.get_asset(seed.asset_id)
        preset = self._repo.get_preset(seed.preset_id) if seed.preset_id else None
        if asset is None:
            return
        parameters = preset.parameters if preset else {}
        result = self._build_result(
            operation=seed.operation,
            asset=asset,
            parameters=parameters,
            preset_id=seed.preset_id,
            job_id=seed.id,
        )
        seed.result_json = result.model_dump_json()

    @staticmethod
    def _asset_read(record: AssetRecord) -> AssetRead:
        return AssetRead(
            id=record.id,
            owner_id=record.owner_id,
            filename=record.filename,
            mime_type=record.mime_type,
            kind=record.kind,
            size_bytes=record.size_bytes,
            width_px=record.width_px,
            height_px=record.height_px,
            duration_ms=record.duration_ms,
            created_at=record.created_at,
        )

    @staticmethod
    def _preset_read(record: PresetRecord) -> PresetRead:
        return PresetRead(
            id=record.id,
            owner_id=record.owner_id,
            name=record.name,
            operation=record.operation,
            parameters=record.parameters,
            created_at=record.created_at,
        )

    def _job_read(self, job: JobRecord, *, preset_name: str | None = None) -> JobRead:
        asset = self._repo.get_asset(job.asset_id)
        filename = asset.filename if asset else "Unknown"
        if preset_name is None and job.preset_id is not None:
            preset = self._repo.get_preset(job.preset_id)
            preset_name = preset.name if preset else None
        result: JobResult | None = None
        if job.result_json and job.status is JobStatus.COMPLETED:
            result = JobResult.model_validate_json(job.result_json)
        return JobRead(
            id=job.id,
            owner_id=job.owner_id,
            asset_id=job.asset_id,
            asset_filename=filename,
            preset_id=job.preset_id,
            preset_name=preset_name,
            status=job.status,
            result=result,
            error_message=job.error_message,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
