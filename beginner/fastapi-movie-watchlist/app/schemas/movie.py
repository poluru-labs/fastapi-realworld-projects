from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_text(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


def _normalize_imdb_id(value: str) -> str:
    return value.strip().casefold()


class WatchStatus(StrEnum):
    WANT_TO_WATCH = "want_to_watch"
    WATCHING = "watching"
    WATCHED = "watched"


class MovieCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Movie title.")
    director: str = Field(..., min_length=1, max_length=120, description="Primary director.")
    imdb_id: str | None = Field(
        default=None,
        max_length=20,
        description="Optional IMDb id (e.g. tt1375666). Must be unique when set.",
    )
    genre: str = Field(default="Drama", max_length=60, description="Primary genre label.")
    release_year: int | None = Field(
        default=None,
        ge=1888,
        le=2100,
        description="Theatrical release year.",
    )
    runtime_minutes: int | None = Field(
        default=None,
        ge=1,
        le=600,
        description="Runtime in minutes.",
    )
    status: WatchStatus = Field(
        default=WatchStatus.WANT_TO_WATCH,
        description="Your watch progress for this title.",
    )
    pinned: bool = Field(
        default=False,
        description="Pinned titles sort to the top of the list (watch next).",
    )

    @field_validator("title", "director", "genre", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("imdb_id", mode="before")
    @classmethod
    def strip_imdb(cls, value: object) -> object:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class MovieUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    director: str | None = Field(default=None, min_length=1, max_length=120)
    imdb_id: str | None = Field(default=None, max_length=20)
    genre: str | None = Field(default=None, max_length=60)
    release_year: int | None = Field(default=None, ge=1888, le=2100)
    runtime_minutes: int | None = Field(default=None, ge=1, le=600)
    status: WatchStatus | None = None
    pinned: bool | None = None

    @field_validator("title", "director", "genre", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("imdb_id", mode="before")
    @classmethod
    def strip_imdb(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class MovieRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    director: str
    imdb_id: str | None
    genre: str
    release_year: int | None
    runtime_minutes: int | None
    status: WatchStatus
    pinned: bool


class MovieDeleteResponse(BaseModel):
    deleted: bool = True
    movie: MovieRead
