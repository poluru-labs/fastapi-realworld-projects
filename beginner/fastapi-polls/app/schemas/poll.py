from pydantic import BaseModel, ConfigDict, Field, field_validator


class PollOptionRead(BaseModel):
    """A single answer choice with its current vote count."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Option id within the poll")
    text: str = Field(..., min_length=1, max_length=100, description="Answer label")
    votes: int = Field(0, ge=0, description="Number of votes recorded for this option")


class PollBase(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="The question voters answer",
        examples=["What is your favorite season?"],
    )


class PollCreate(PollBase):
    options: list[str] = Field(
        ...,
        min_length=2,
        max_length=10,
        description="Two or more unique answer choices",
        examples=[["Spring", "Summer", "Fall", "Winter"]],
    )

    @field_validator("options")
    @classmethod
    def normalize_options(cls, value: list[str]) -> list[str]:
        cleaned = [option.strip() for option in value if option.strip()]
        if len(cleaned) < 2:
            raise ValueError("Provide at least two non-empty options")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Options must be unique")
        return cleaned


class PollUpdate(BaseModel):
    question: str | None = Field(
        None,
        min_length=1,
        max_length=200,
        description="New question text",
    )
    options: list[str] | None = Field(
        None,
        min_length=2,
        max_length=10,
        description="Replace all choices (resets vote counts)",
    )

    @field_validator("options")
    @classmethod
    def normalize_options(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [option.strip() for option in value if option.strip()]
        if len(cleaned) < 2:
            raise ValueError("Provide at least two non-empty options")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Options must be unique")
        return cleaned


class PollRead(PollBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Poll id")
    options: list[PollOptionRead] = Field(..., description="Choices and vote totals")


class PollDeleteResponse(BaseModel):
    deleted: bool = True
    poll: PollRead


class VoteCreate(BaseModel):
    option_id: int = Field(..., ge=1, description="Id of the option to vote for")
