import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

UPLOAD_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,62}[a-z0-9]$")


class UploadStatus(StrEnum):
    INITIATED = "initiated"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    ABORTED = "aborted"


class UploadCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "key": "release-assets",
                    "filename": "app-release.zip",
                    "content_type": "application/zip",
                    "total_bytes": 1_048_576,
                    "chunk_size_bytes": 262_144,
                }
            ]
        },
    )

    key: str = Field(..., min_length=2, max_length=64, pattern=UPLOAD_KEY_PATTERN.pattern)
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(default="application/octet-stream", max_length=120)
    total_bytes: int = Field(..., ge=1, le=5_368_709_120)
    chunk_size_bytes: int = Field(default=262_144, ge=250, le=8_388_608)


class UploadRead(BaseModel):
    id: int
    key: str
    filename: str
    content_type: str
    total_bytes: int
    chunk_size_bytes: int
    status: UploadStatus
    bytes_received: int
    parts_received: int
    expected_parts: int
    created_at: datetime
    completed_at: datetime | None


class UploadProvisioned(UploadRead):
    upload_token: str = Field(description="One-time token for part uploads and complete.")


class UploadStatusDetail(UploadRead):
    missing_part_indexes: list[int]
    progress_percent: float


class PartRead(BaseModel):
    upload_key: str
    part_index: int
    byte_start: int
    byte_end: int
    size_bytes: int
    bytes_received: int
    status: UploadStatus
