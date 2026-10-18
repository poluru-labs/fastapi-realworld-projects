from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DocumentVisibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class DocumentStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class MemberRole(StrEnum):
    EDITOR = "editor"
    VIEWER = "viewer"


class SyncStatus(StrEnum):
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"


class TextPatch(BaseModel):
    """Single contiguous edit: delete `delete` chars from `start`, then insert text."""

    start: int = Field(ge=0)
    delete: int = Field(ge=0)
    insert: str = Field(default="", max_length=8000)


class DocumentCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(default="", max_length=200_000)
    visibility: DocumentVisibility = DocumentVisibility.PUBLIC


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    body: str
    revision: int
    visibility: DocumentVisibility
    status: DocumentStatus
    owner_id: int
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    role: MemberRole
    last_seen_revision: int
    joined_at: datetime


class SeenRevisionUpdate(BaseModel):
    last_seen_revision: int = Field(ge=0)


class EditSubmit(BaseModel):
    base_revision: int = Field(
        ge=0,
        description="Must match the document revision you edited against.",
    )
    patch: TextPatch

    @model_validator(mode="after")
    def patch_has_effect(self) -> "EditSubmit":
        if self.patch.delete == 0 and not self.patch.insert:
            raise ValueError("Patch must delete or insert at least one character")
        return self


class RevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    author_id: int
    revision: int
    base_revision: int
    patch: TextPatch
    created_at: datetime


class SyncRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    revision_id: int
    document_id: int
    recipient_id: int
    status: SyncStatus
    lease_holder: str | None
    version: int
    synced_at: datetime | None
    created_at: datetime


class SyncRegister(BaseModel):
    node_id: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    document_slugs: list[str] = Field(default_factory=list, max_length=32)


class SyncHeartbeat(BaseModel):
    node_id: str = Field(min_length=2, max_length=64)


class ClaimSyncRequest(BaseModel):
    node_id: str = Field(min_length=2, max_length=64)


class CompleteSyncRequest(BaseModel):
    node_id: str = Field(min_length=2, max_length=64)
    expected_version: int = Field(ge=1)
