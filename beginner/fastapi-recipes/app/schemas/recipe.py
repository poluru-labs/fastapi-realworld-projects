from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _strip_text(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class RecipeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Recipe name.")
    chef: str = Field(..., min_length=1, max_length=120, description="Chef or source name.")
    source_url: str | None = Field(
        default=None,
        max_length=500,
        description="Optional link to the original recipe. Must be unique when set.",
    )
    cuisine: str = Field(default="General", max_length=60, description="Cuisine or style.")
    prep_minutes: int | None = Field(default=None, ge=1, le=600)
    cook_minutes: int | None = Field(default=None, ge=1, le=600)
    servings: int = Field(default=4, ge=1, le=50)
    difficulty: Difficulty = Field(default=Difficulty.EASY)
    vegetarian: bool = Field(default=False)
    steps: str = Field(default="", max_length=4000, description="Cooking directions.")
    featured: bool = Field(default=False, description="Featured recipes sort to the top.")

    @field_validator("title", "chef", "cuisine", "steps", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("source_url", mode="before")
    @classmethod
    def strip_url(cls, value: object) -> object:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class RecipeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    chef: str | None = Field(default=None, min_length=1, max_length=120)
    source_url: str | None = Field(default=None, max_length=500)
    cuisine: str | None = Field(default=None, max_length=60)
    prep_minutes: int | None = Field(default=None, ge=1, le=600)
    cook_minutes: int | None = Field(default=None, ge=1, le=600)
    servings: int | None = Field(default=None, ge=1, le=50)
    difficulty: Difficulty | None = None
    vegetarian: bool | None = None
    steps: str | None = Field(default=None, max_length=4000)
    featured: bool | None = None

    @field_validator("title", "chef", "cuisine", "steps", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("source_url", mode="before")
    @classmethod
    def strip_url(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class RecipeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    chef: str
    source_url: str | None
    cuisine: str
    prep_minutes: int | None
    cook_minutes: int | None
    total_minutes: int | None
    servings: int
    difficulty: Difficulty
    vegetarian: bool
    steps: str
    featured: bool

    @model_validator(mode="after")
    def compute_total(self) -> "RecipeRead":
        parts = [value for value in (self.prep_minutes, self.cook_minutes) if value is not None]
        self.total_minutes = sum(parts) if parts else None
        return self


class RecipeDeleteResponse(BaseModel):
    deleted: bool = True
    recipe: RecipeRead
