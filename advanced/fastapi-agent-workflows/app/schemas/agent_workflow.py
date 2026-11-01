import re
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class WorkflowStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class StepType(StrEnum):
    AGENT = "agent"
    TOOL = "tool"


class RunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStep(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    type: StepType
    prompt_template: str | None = Field(default=None, max_length=4000)
    tool_name: str | None = Field(default=None, max_length=64)
    input_from: str | None = Field(
        default=None,
        max_length=64,
        description="Context key to read as primary input (defaults to prior step output).",
    )

    @model_validator(mode="after")
    def validate_step_shape(self) -> "WorkflowStep":
        if self.type == StepType.AGENT and not self.prompt_template:
            raise ValueError("agent steps require prompt_template")
        if self.type == StepType.TOOL and not self.tool_name:
            raise ValueError("tool steps require tool_name")
        return self


class WorkflowDefinitionCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    steps: list[WorkflowStep] = Field(min_length=1, max_length=20)

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        slug = value.strip().lower()
        if not SLUG_PATTERN.fullmatch(slug):
            msg = "slug must be lowercase letters, numbers, and hyphens"
            raise ValueError(msg)
        return slug

    @model_validator(mode="after")
    def unique_step_keys(self) -> "WorkflowDefinitionCreate":
        keys = [step.key for step in self.steps]
        if len(keys) != len(set(keys)):
            raise ValueError("step keys must be unique within a workflow")
        return self


class WorkflowDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str
    status: WorkflowStatus
    steps: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class WorkflowDefinitionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    steps: list[WorkflowStep] | None = Field(default=None, min_length=1, max_length=20)


class RunCreate(BaseModel):
    workflow_slug: str = Field(min_length=2, max_length=64)
    input: dict[str, Any] = Field(default_factory=dict)


class StepLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sequence: int
    step_key: str
    step_type: StepType
    status: StepStatus
    input_payload: dict[str, Any]
    output_payload: dict[str, Any]
    created_at: datetime


class RunRead(BaseModel):
    id: int
    workflow_slug: str
    status: RunStatus
    input: dict[str, Any]
    output: dict[str, Any]
    context: dict[str, Any]
    idempotency_key: str
    steps: list[StepLogRead]
    created_at: datetime
    finished_at: datetime | None
