from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_current_user, get_team_service
from app.schemas.task import TaskCreate, TaskRead, TaskStatus, TaskUpdate
from app.schemas.user import UserRead
from app.services.team_service import TeamService

router = APIRouter()

_CREATE_EXAMPLES = {
    "unassigned": {
        "summary": "Todo with no assignee",
        "value": {"title": "Sketch the board", "description": "First pass at the columns"},
    },
    "assigned": {
        "summary": "Todo assigned to a member",
        "description": "assignee_email must already be on the team.",
        "value": {
            "title": "Review the palette",
            "description": "",
            "assignee_email": "admin@example.com",
        },
    },
}


@router.get(
    "",
    response_model=list[TaskRead],
    summary="List tasks on a team",
    description=(
        "Members and platform admins. Filter with `status` and `assignee_id`. "
        "Results are ordered by id."
    ),
)
def list_tasks(
    team_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
    task_status: Annotated[
        TaskStatus | None,
        Query(alias="status", description="Keep only tasks in this status"),
    ] = None,
    assignee_id: Annotated[
        int | None,
        Query(description="Keep only tasks assigned to this user id"),
    ] = None,
) -> list[TaskRead]:
    return service.list_tasks(actor, team_id, status=task_status, assignee_id=assignee_id)


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
    description=(
        "Any team member, or a platform admin. New tasks always start as `todo`. "
        "Move them with PATCH. An assignee must already be a member."
    ),
    responses={
        403: {"description": "Caller is not a member of this team."},
        409: {"description": "Assignee email is a user who is not on the team."},
    },
)
def create_task(
    team_id: int,
    payload: Annotated[TaskCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> TaskRead:
    return service.create_task(actor, team_id, payload)


@router.get(
    "/{task_id}",
    response_model=TaskRead,
    summary="Get one task",
    description="404 when the id is missing or belongs to a different team.",
)
def get_task(
    team_id: int,
    task_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> TaskRead:
    return service.get_task(actor, team_id, task_id)


@router.patch(
    "/{task_id}",
    response_model=TaskRead,
    summary="Update a task",
    description=(
        "Members may change title, description, assignee, and status. "
        "Status moves one step at a time: `todo` → `in_progress` → `done`, "
        "and `done` can return to `in_progress`. `todo` cannot jump straight to `done`."
    ),
    responses={
        409: {"description": "Status transition is not allowed, or the assignee is not a member."},
    },
)
def update_task(
    team_id: int,
    task_id: int,
    payload: TaskUpdate,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> TaskRead:
    return service.update_task(actor, team_id, task_id, payload)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    description="The user who created it, the team owner, or a platform admin.",
    responses={403: {"description": "A regular member cannot delete someone else's task."}},
)
def delete_task(
    team_id: int,
    task_id: int,
    actor: Annotated[UserRead, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> None:
    service.delete_task(actor, team_id, task_id)
