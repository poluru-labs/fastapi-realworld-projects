from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_todo_service
from app.schemas.todo import Priority, TodoCreate, TodoDeleteResponse, TodoRead, TodoUpdate
from app.services.todo_service import TodoService

router = APIRouter()

_CREATE_EXAMPLES = {
    "open_task": {
        "summary": "New open task",
        "description": "Title is required. Notes, priority, and completed have defaults.",
        "value": {"title": "Write the README", "notes": "Include a curl walkthrough"},
    },
    "already_done": {
        "summary": "Task that is already finished",
        "description": "Set completed to true when you are recording work that is done.",
        "value": {
            "title": "Install Python 3.11",
            "priority": "low",
            "completed": True,
        },
    },
}

_UPDATE_EXAMPLES = {
    "rename": {
        "summary": "Change the title only",
        "description": "Omitted fields stay as they are.",
        "value": {"title": "Write the API guide"},
    },
    "raise_priority": {
        "summary": "Mark it high priority and unfinished",
        "value": {"priority": "high", "completed": False},
    },
}


@router.get(
    "",
    response_model=list[TodoRead],
    summary="List todos",
    description=(
        "Returns every todo, oldest id first. "
        "Pass completed to keep only open or finished tasks. "
        "Pass priority to keep one urgency level. Both filters can be used together."
    ),
)
def list_todos(
    service: Annotated[TodoService, Depends(get_todo_service)],
    completed: Annotated[
        bool | None,
        Query(description="true for finished tasks, false for open tasks."),
    ] = None,
    priority: Annotated[
        Priority | None,
        Query(description="low, medium, or high."),
    ] = None,
) -> list[TodoRead]:
    return service.list_todos(completed=completed, priority=priority)


@router.get(
    "/{todo_id}",
    response_model=TodoRead,
    summary="Get a todo",
    responses={404: {"description": "No todo has that id."}},
)
def get_todo(
    todo_id: int,
    service: Annotated[TodoService, Depends(get_todo_service)],
) -> TodoRead:
    return service.get_todo(todo_id)


@router.post(
    "",
    response_model=TodoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a todo",
    description=(
        "Title is required, 1–120 characters after trimming spaces. "
        "Notes may be blank and are at most 500 characters. "
        "Priority defaults to medium. Completed defaults to false."
    ),
    responses={422: {"description": "The body failed validation."}},
)
def create_todo(
    payload: Annotated[TodoCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
    service: Annotated[TodoService, Depends(get_todo_service)],
) -> TodoRead:
    return service.create_todo(payload)


@router.patch(
    "/{todo_id}",
    response_model=TodoRead,
    summary="Update a todo",
    description=(
        "Send only the fields you want to change. "
        "An empty body returns the todo unchanged. "
        "Setting completed here is the same as complete or reopen."
    ),
    responses={
        404: {"description": "No todo has that id."},
        422: {"description": "A sent field failed validation."},
    },
)
def update_todo(
    todo_id: int,
    payload: Annotated[TodoUpdate, Body(openapi_examples=_UPDATE_EXAMPLES)],
    service: Annotated[TodoService, Depends(get_todo_service)],
) -> TodoRead:
    return service.update_todo(todo_id, payload)


@router.post(
    "/{todo_id}/complete",
    response_model=TodoRead,
    summary="Mark a todo complete",
    description=(
        "Sets completed to true. Calling it again on a finished todo leaves the todo as it is."
    ),
    responses={404: {"description": "No todo has that id."}},
)
def complete_todo(
    todo_id: int,
    service: Annotated[TodoService, Depends(get_todo_service)],
) -> TodoRead:
    return service.complete_todo(todo_id)


@router.post(
    "/{todo_id}/reopen",
    response_model=TodoRead,
    summary="Reopen a todo",
    description=(
        "Sets completed to false. Calling it again on an open todo leaves the todo as it is."
    ),
    responses={404: {"description": "No todo has that id."}},
)
def reopen_todo(
    todo_id: int,
    service: Annotated[TodoService, Depends(get_todo_service)],
) -> TodoRead:
    return service.reopen_todo(todo_id)


@router.delete(
    "/{todo_id}",
    response_model=TodoDeleteResponse,
    summary="Delete a todo",
    description="Removes the todo and returns a snapshot of what was deleted.",
    responses={404: {"description": "No todo has that id."}},
)
def delete_todo(
    todo_id: int,
    service: Annotated[TodoService, Depends(get_todo_service)],
) -> TodoDeleteResponse:
    removed = service.delete_todo(todo_id)
    return TodoDeleteResponse(todo=removed)
