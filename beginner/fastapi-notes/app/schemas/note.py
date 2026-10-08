from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_text(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120, description="Short name of the note.")
    body: str = Field(
        "",
        max_length=2_000,
        description="The note text. Blank is allowed.",
    )
    pinned: bool = Field(False, description="Pinned notes stay at the top of the list.")

    @field_validator("title", "body", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)


class NoteUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=120)
    body: str | None = Field(None, max_length=2_000)
    pinned: bool | None = None

    @field_validator("title", "body", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    pinned: bool


class NoteDeleteResponse(BaseModel):
    deleted: bool = True
    note: NoteRead
