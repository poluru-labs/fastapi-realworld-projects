from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.core.constants import DEFAULT_TOP_N, MAX_TEXT_LENGTH, MAX_TOP_N


def _reject_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("text must contain at least one non-whitespace character")
    return value


class TransformMode(StrEnum):
    """Case and shape changes. Analysis endpoints do not use these."""

    lower = "lower"
    upper = "upper"
    title = "title"
    reverse = "reverse"
    slug = "slug"


class WordCount(BaseModel):
    word: str = Field(..., description="Lowercase token")
    count: int = Field(..., ge=1)


class AnalyzeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TEXT_LENGTH,
        description="Text to measure. Leading and trailing spaces are kept in character counts.",
        examples=["Hello, world! Hello."],
    )
    top_n: int = Field(
        DEFAULT_TOP_N,
        ge=1,
        le=MAX_TOP_N,
        description="How many ranked words to return",
    )
    ignore_stop_words: bool = Field(
        False,
        description=(
            "When true, top_words skips the stop-word catalog. Other counts still include them."
        ),
    )

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        return _reject_blank(value)


class AnalyzeRead(BaseModel):
    characters: int = Field(..., description="Length of the submitted text, including spaces")
    characters_no_spaces: int = Field(..., description="Characters that are not Unicode whitespace")
    words: int
    unique_words: int = Field(..., description="Distinct words, compared case-insensitively")
    sentences: int
    paragraphs: int
    average_word_length: float = Field(
        ...,
        description=(
            "Mean token length, rounded half-up to 2 decimal places. 0 when there are no words."
        ),
    )
    reading_time_seconds: int = Field(
        ...,
        description=(
            "Estimated spoken time at 200 words per minute, rounded half-up to whole seconds"
        ),
    )
    is_palindrome: bool = Field(
        ...,
        description=(
            "True when letters and digits read the same forward and backward, ignoring case"
        ),
    )
    top_words: list[WordCount]


class TransformRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TEXT_LENGTH,
        examples=["Hello, World!"],
    )
    mode: TransformMode = Field(..., description="lower, upper, title, reverse, or slug")

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        return _reject_blank(value)


class TransformRead(BaseModel):
    mode: TransformMode
    original: str = Field(..., description="The text submitted in the request")
    result: str


class AnalyzerOptionsRead(BaseModel):
    reading_words_per_minute: int
    max_text_length: int
    max_top_n: int
    transform_modes: list[TransformMode]
    stop_word_count: int
    stop_words: list[str] = Field(
        ...,
        description=(
            "Lowercase function words omitted from top_words when ignore_stop_words is true"
        ),
    )
