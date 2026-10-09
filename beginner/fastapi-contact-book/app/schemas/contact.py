from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _strip_text(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


class ContactCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120, description="Display name.")
    email: EmailStr | None = Field(
        default=None,
        description="Optional. When set, must be unique in the book (case insensitive).",
    )
    phone: str = Field(default="", max_length=32, description="Optional phone number.")
    company: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=500)
    favorite: bool = Field(default=False, description="Favorites sort to the top of the list.")

    @field_validator("full_name", "phone", "company", "notes", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value: object) -> object:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class ContactUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    company: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)
    favorite: bool | None = None

    @field_validator("full_name", "phone", "company", "notes", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str | None
    phone: str
    company: str
    notes: str
    favorite: bool


class ContactDeleteResponse(BaseModel):
    deleted: bool = True
    contact: ContactRead
