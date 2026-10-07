from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def _strip_text(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120, description="Short name of the task.")
    notes: str = Field("", max_length=500, description="Optional extra detail. Blank is allowed.")
    priority: Priority = Field(
        Priority.MEDIUM,
        description="How urgent the task is: low, medium, or high.",
    )
    completed: bool = Field(False, description="True when the task is already finished.")

    @field_validator("title", "notes", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)


class TodoUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=120)
    notes: str | None = Field(None, max_length=500)
    priority: Priority | None = None
    completed: bool | None = None

    @field_validator("title", "notes", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    notes: str
    priority: Priority
    completed: bool


class TodoDeleteResponse(BaseModel):
    deleted: bool = True
    todo: TodoRead
