from pydantic import BaseModel, ConfigDict, Field


class ProviderCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=120, examples=["Dr Ada Lovelace"])
    specialty: str = Field(
        default="",
        max_length=120,
        description="Short label shown on the booking screen.",
        examples=["General practice"],
    )


class ProviderUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    specialty: str | None = Field(default=None, max_length=120)


class ProviderRead(BaseModel):
    id: int
    name: str
    specialty: str
    is_active: bool
