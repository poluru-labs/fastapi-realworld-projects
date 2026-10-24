from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MediaKind(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class MediaOperation(StrEnum):
    THUMBNAIL = "thumbnail"
    RESIZE = "resize"
    TRANSCODE = "transcode"
    EXTRACT_AUDIO = "extract_audio"


class JobStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class AssetCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "filename": "hero-banner.jpg",
                    "mime_type": "image/jpeg",
                    "kind": "image",
                    "size_bytes": 2480000,
                    "width_px": 2400,
                    "height_px": 1600,
                    "duration_ms": None,
                }
            ]
        },
    )

    filename: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=3, max_length=120)
    kind: MediaKind
    size_bytes: int = Field(..., ge=1, le=50_000_000_000)
    width_px: int | None = Field(default=None, ge=1, le=30_000)
    height_px: int | None = Field(default=None, ge=1, le=30_000)
    duration_ms: int | None = Field(default=None, ge=1, le=86_400_000)


class AssetUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    filename: str | None = Field(default=None, min_length=1, max_length=255)


class AssetRead(BaseModel):
    id: int
    owner_id: int
    filename: str
    mime_type: str
    kind: MediaKind
    size_bytes: int
    width_px: int | None
    height_px: int | None
    duration_ms: int | None
    created_at: datetime


class PresetCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "name": "Web thumbnail",
                    "operation": "thumbnail",
                    "parameters": {"width": 320, "height": 180},
                }
            ]
        },
    )

    name: str = Field(..., min_length=1, max_length=120)
    operation: MediaOperation
    parameters: dict[str, Any] = Field(default_factory=dict)


class PresetUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    operation: MediaOperation | None = None
    parameters: dict[str, Any] | None = None


class PresetRead(BaseModel):
    id: int
    owner_id: int
    name: str
    operation: MediaOperation
    parameters: dict[str, Any]
    created_at: datetime


class JobSubmit(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"asset_id": 1, "preset_id": 1},
                {
                    "asset_id": 2,
                    "operation": "transcode",
                    "parameters": {"format": "webm"},
                },
            ]
        },
    )

    asset_id: int = Field(..., ge=1)
    preset_id: int | None = Field(default=None, ge=1)
    operation: MediaOperation | None = None
    parameters: dict[str, Any] | None = None

    @model_validator(mode="after")
    def preset_xor_inline(self) -> Self:
        has_preset = self.preset_id is not None
        has_inline = self.operation is not None
        if has_preset == has_inline:
            raise ValueError("Provide exactly one of preset_id or operation")
        if has_inline and self.parameters is None:
            raise ValueError("parameters are required when operation is set")
        return self


class JobOutput(BaseModel):
    output_uri: str
    mime_type: str
    size_bytes: int
    width_px: int | None = None
    height_px: int | None = None
    duration_ms: int | None = None


class JobResult(BaseModel):
    operation: MediaOperation
    source_asset_id: int
    preset_id: int | None
    output: JobOutput
    notes: str


class JobRead(BaseModel):
    id: int
    owner_id: int
    asset_id: int
    asset_filename: str
    preset_id: int | None
    preset_name: str | None
    status: JobStatus
    result: JobResult | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class OperationCatalogEntry(BaseModel):
    operation: MediaOperation
    description: str
    allowed_kinds: list[MediaKind]
    parameter_schema: dict[str, Any]
