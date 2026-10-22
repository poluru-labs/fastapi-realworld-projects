from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class QuizStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class QuizCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "HTTP trivia",
                    "description": "Short quiz about status codes and methods.",
                }
            ]
        },
    )

    title: str = Field(..., min_length=1, max_length=120, examples=["Python basics"])
    description: str = Field(default="", max_length=2000)


class QuizUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class QuizRead(BaseModel):
    id: int
    title: str
    description: str
    status: QuizStatus
    question_count: int
    created_at: datetime
    updated_at: datetime


class QuestionCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "prompt": "Which HTTP method is idempotent for updates?",
                    "choices": ["GET", "POST", "PUT", "CONNECT"],
                    "correct_index": 2,
                }
            ]
        },
    )

    prompt: str = Field(..., min_length=1, max_length=2000)
    choices: list[str] = Field(..., min_length=2, max_length=6)
    correct_index: int = Field(..., ge=0, description="Zero-based index into `choices`.")

    @field_validator("choices")
    @classmethod
    def strip_choices(cls, choices: list[str]) -> list[str]:
        cleaned = [c.strip() for c in choices if c.strip()]
        if len(cleaned) < 2:
            raise ValueError("At least two non-empty choices are required")
        return cleaned

    @model_validator(mode="after")
    def index_in_range(self) -> Self:
        if self.correct_index >= len(self.choices):
            raise ValueError("correct_index must point at one of the choices")
        return self


class QuestionUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    prompt: str | None = Field(default=None, min_length=1, max_length=2000)
    choices: list[str] | None = Field(default=None, min_length=2, max_length=6)
    correct_index: int | None = Field(default=None, ge=0)


class QuestionAuthorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    prompt: str
    choices: list[str]
    correct_index: int
    position: int


class QuestionPlayerRead(BaseModel):
    id: int
    quiz_id: int
    prompt: str
    choices: list[str]
    position: int


class QuizAuthorDetail(QuizRead):
    questions: list[QuestionAuthorRead]


class QuizPlayerDetail(QuizRead):
    questions: list[QuestionPlayerRead]


class AnswerSubmission(BaseModel):
    question_id: int = Field(..., ge=1)
    choice_index: int = Field(..., ge=0)


class QuizSubmit(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "participant_name": "Alex",
                    "answers": [
                        {"question_id": 1, "choice_index": 1},
                        {"question_id": 2, "choice_index": 1},
                        {"question_id": 3, "choice_index": 1},
                    ],
                }
            ]
        },
    )

    participant_name: str = Field(default="Anonymous", max_length=120)
    answers: list[AnswerSubmission] = Field(..., min_length=1)


class QuestionResult(BaseModel):
    question_id: int
    correct: bool
    chosen_index: int
    correct_index: int | None = Field(
        default=None,
        description="Included so learners can review after submit.",
    )


class QuizSubmitResult(BaseModel):
    quiz_id: int
    participant_name: str
    score: int
    total_questions: int
    percentage: float
    results: list[QuestionResult]
