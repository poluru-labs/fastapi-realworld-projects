import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

COLLECTION_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CollectionCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        slug = value.strip().lower()
        if not COLLECTION_SLUG_PATTERN.fullmatch(slug):
            msg = "slug must be lowercase letters, numbers, and hyphens"
            raise ValueError(msg)
        return slug


class CollectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str
    created_at: datetime


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source_uri: str = Field(default="", max_length=500)
    text: str = Field(min_length=1, max_length=100_000)


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    title: str
    source_uri: str
    chunk_count: int
    created_at: datetime


class CitationRead(BaseModel):
    document_id: int
    document_title: str
    chunk_index: int
    excerpt: str
    score: float


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=10)


class QueryResponse(BaseModel):
    collection_slug: str
    question: str
    answer: str
    citations: list[CitationRead]
