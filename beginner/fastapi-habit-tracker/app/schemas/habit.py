from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_text(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


class HabitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80, description="Habit label.")
    category: str = Field(default="General", max_length=40)
    target_days_per_week: int = Field(
        default=3,
        ge=1,
        le=7,
        description="Weekly goal used by stats (not enforced on check-in).",
    )
    note: str = Field(default="", max_length=300)

    @field_validator("name", "category", "note", mode="before")
    @classmethod
    def strip_fields(cls, value: object) -> object:
        return _strip_text(value)


class HabitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    category: str | None = Field(default=None, max_length=40)
    target_days_per_week: int | None = Field(default=None, ge=1, le=7)
    note: str | None = Field(default=None, max_length=300)

    @field_validator("name", "category", "note", mode="before")
    @classmethod
    def strip_fields(cls, value: object) -> object:
        return _strip_text(value)


class HabitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    target_days_per_week: int
    note: str
    paused: bool


class HabitDeleteResponse(BaseModel):
    deleted: bool = True
    habit: HabitRead


class CheckInCreate(BaseModel):
    checked_on: date = Field(..., description="Calendar day you completed the habit.")
    note: str = Field(default="", max_length=200)

    @field_validator("note", mode="before")
    @classmethod
    def strip_note(cls, value: object) -> object:
        return _strip_text(value)


class CheckInRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    habit_id: int
    checked_on: date
    note: str


class CheckInDeleteResponse(BaseModel):
    deleted: bool = True
    check_in: CheckInRead


class HabitStats(BaseModel):
    habit_id: int
    current_streak: int = Field(description="Consecutive days ending on the latest check-in.")
    total_check_ins: int
    check_ins_this_week: int
    on_target_this_week: bool = Field(
        description="True when check_ins_this_week >= target_days_per_week.",
    )
