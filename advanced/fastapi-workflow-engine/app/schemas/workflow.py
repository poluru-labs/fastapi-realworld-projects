"""Workflow definition graph and instance command schemas."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.user import UserRole


class DefinitionStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class InstanceStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"


class WorkflowEventType(StrEnum):
    INSTANCE_STARTED = "instance_started"
    STATE_CHANGED = "state_changed"


class TransitionSpec(BaseModel):
    """One directed edge in the definition graph."""

    model_config = ConfigDict(populate_by_name=True)

    action: str = Field(min_length=1, max_length=64)
    from_state: str = Field(alias="from", min_length=1, max_length=64)
    to_state: str = Field(alias="to", min_length=1, max_length=64)
    roles: list[UserRole] = Field(
        default_factory=list,
        description="When non-empty, only listed roles (or platform admin) may fire this action.",
    )


class WorkflowDefinitionCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    initial_state: str = Field(min_length=1, max_length=64)
    states: list[str] = Field(min_length=1, max_length=32)
    transitions: list[TransitionSpec] = Field(min_length=1, max_length=64)
    terminal_states: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("states")
    @classmethod
    def unique_states(cls, states: list[str]) -> list[str]:
        if len(set(states)) != len(states):
            raise ValueError("states must be unique")
        return states

    @model_validator(mode="after")
    def validate_graph(self) -> "WorkflowDefinitionCreate":
        state_set = set(self.states)
        if self.initial_state not in state_set:
            raise ValueError("initial_state must appear in states")
        for terminal in self.terminal_states:
            if terminal not in state_set:
                raise ValueError("terminal_states must be a subset of states")
        for edge in self.transitions:
            if edge.from_state not in state_set or edge.to_state not in state_set:
                raise ValueError("transition endpoints must be listed in states")
        return self


class WorkflowDefinitionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    initial_state: str | None = Field(default=None, min_length=1, max_length=64)
    states: list[str] | None = Field(default=None, min_length=1, max_length=32)
    transitions: list[TransitionSpec] | None = Field(default=None, min_length=1, max_length=64)
    terminal_states: list[str] | None = Field(default=None, max_length=32)


class WorkflowDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str
    status: DefinitionStatus
    initial_state: str
    states: list[str]
    transitions: list[TransitionSpec]
    terminal_states: list[str]
    created_at: datetime
    updated_at: datetime


class InstanceStart(BaseModel):
    definition_slug: str = Field(min_length=1, max_length=64)
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Opaque JSON bag copied onto the instance and echoed in events.",
    )


class TransitionCommand(BaseModel):
    action: str = Field(min_length=1, max_length=64)
    expected_version: int = Field(ge=1, description="Optimistic lock from the last GET.")
    context_patch: dict[str, Any] = Field(
        default_factory=dict,
        description="Shallow-merged into instance context when the transition succeeds.",
    )
    note: str = Field(default="", max_length=500)


class WorkflowInstanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    definition_id: int
    definition_slug: str
    owner_id: int
    owner_name: str
    current_state: str
    status: InstanceStatus
    context: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime


class WorkflowEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    instance_id: int
    sequence: int
    event_type: WorkflowEventType
    from_state: str | None
    to_state: str | None
    action: str | None
    payload: dict[str, Any]
    actor_id: int
    created_at: datetime
