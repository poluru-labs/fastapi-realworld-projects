from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_text(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


def _normalize_isbn(value: str) -> str:
    return value.replace("-", "").replace(" ", "").upper()


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Book title.")
    author: str = Field(..., min_length=1, max_length=120, description="Primary author.")
    isbn: str | None = Field(
        default=None,
        max_length=17,
        description="Optional ISBN-10 or ISBN-13. Must be unique when set.",
    )
    genre: str = Field(default="General", max_length=60, description="Shelf category.")
    publication_year: int | None = Field(
        default=None,
        ge=1000,
        le=2100,
        description="Year the edition was published.",
    )
    available: bool = Field(default=True, description="True when copies are on the shelf.")
    featured: bool = Field(default=False, description="Featured titles sort to the top.")

    @field_validator("title", "author", "genre", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("isbn", mode="before")
    @classmethod
    def strip_isbn(cls, value: object) -> object:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=120)
    isbn: str | None = Field(default=None, max_length=17)
    genre: str | None = Field(default=None, max_length=60)
    publication_year: int | None = Field(default=None, ge=1000, le=2100)
    available: bool | None = None
    featured: bool | None = None

    @field_validator("title", "author", "genre", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("isbn", mode="before")
    @classmethod
    def strip_isbn(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str | None
    genre: str
    publication_year: int | None
    available: bool
    featured: bool


class BookDeleteResponse(BaseModel):
    deleted: bool = True
    book: BookRead
