from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeckCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "French greetings",
                    "description": "Common phrases for beginners.",
                }
            ]
        },
    )

    title: str = Field(..., min_length=1, max_length=120, examples=["Spanish basics"])
    description: str = Field(default="", max_length=2000)


class DeckUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class DeckRead(BaseModel):
    id: int
    title: str
    description: str
    card_count: int
    created_at: datetime
    updated_at: datetime


class CardCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "front": "Hola",
                    "back": "Hello",
                    "hint": "Spanish greeting",
                }
            ]
        },
    )

    front: str = Field(..., min_length=1, max_length=2000)
    back: str = Field(..., min_length=1, max_length=2000)
    hint: str | None = Field(default=None, max_length=500)


class CardUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    front: str | None = Field(default=None, min_length=1, max_length=2000)
    back: str | None = Field(default=None, min_length=1, max_length=2000)
    hint: str | None = Field(default=None, max_length=500)


class CardRead(BaseModel):
    id: int
    deck_id: int
    front: str
    back: str
    hint: str | None
    position: int


class CardFrontRead(BaseModel):
    id: int
    deck_id: int
    front: str
    hint: str | None
    position: int


class StudySession(BaseModel):
    deck_id: int
    title: str
    cards: list[CardFrontRead]


class DeckDetail(DeckRead):
    cards: list[CardRead]
