from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, EmailStr, Field, model_validator


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120, examples=["Sketch the board"])
    description: str = Field("", max_length=2000)
    assignee_email: EmailStr | None = Field(
        None,
        description="Must already be a member of the team. Omit to leave the task unassigned.",
    )


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = Field(None, max_length=2000)
    status: TaskStatus | None = None
    assignee_email: EmailStr | None = Field(
        None,
        description="Assign to this member. Omit to leave the assignee unchanged.",
    )
    clear_assignee: bool = Field(
        False,
        description="Set true to unassign. Do not send this together with assignee_email.",
    )

    @model_validator(mode="after")
    def one_assignee_change(self) -> Self:
        email_sent = "assignee_email" in self.model_fields_set and self.assignee_email is not None
        if self.clear_assignee and email_sent:
            raise ValueError("Send either assignee_email or clear_assignee, not both")
        return self


class TaskRead(BaseModel):
    id: int
    team_id: int
    title: str
    description: str
    status: TaskStatus
    assignee_id: int | None
    created_by: int
    created_at: datetime
