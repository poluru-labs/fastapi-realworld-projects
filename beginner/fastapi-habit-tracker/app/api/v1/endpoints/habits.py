from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_habit_service
from app.schemas.habit import (
    CheckInCreate,
    CheckInDeleteResponse,
    CheckInRead,
    HabitCreate,
    HabitDeleteResponse,
    HabitRead,
    HabitStats,
    HabitUpdate,
)
from app.services.habit_service import HabitService

router = APIRouter()

_CREATE_EXAMPLES = {
    "water": {
        "summary": "Daily hydration",
        "value": {
            "name": "Drink water",
            "category": "Health",
            "target_days_per_week": 7,
            "note": "8 glasses",
        },
    }
}

_CHECK_IN_EXAMPLES = {
    "today": {
        "summary": "Log completion",
        "value": {"checked_on": "2026-10-15", "note": "Done before lunch"},
    }
}


@router.get(
    "/categories",
    response_model=list[str],
    summary="List habit categories",
)
def list_categories(service: Annotated[HabitService, Depends(get_habit_service)]) -> list[str]:
    return service.list_categories()


@router.get(
    "",
    response_model=list[HabitRead],
    summary="List habits",
    description="Paused habits sort last. Filter by category, paused flag, or text search.",
)
def list_habits(
    service: Annotated[HabitService, Depends(get_habit_service)],
    category: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    paused: Annotated[bool | None, Query()] = None,
) -> list[HabitRead]:
    return service.list_habits(category=category, search=search, paused=paused)


@router.get("/{habit_id}", response_model=HabitRead, summary="Get one habit")
def get_habit(
    habit_id: int,
    service: Annotated[HabitService, Depends(get_habit_service)],
) -> HabitRead:
    return service.get_habit(habit_id)


@router.post(
    "",
    response_model=HabitRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a habit",
)
def create_habit(
    service: Annotated[HabitService, Depends(get_habit_service)],
    payload: Annotated[HabitCreate, Body(openapi_examples=_CREATE_EXAMPLES)],
) -> HabitRead:
    return service.create_habit(payload)


@router.patch("/{habit_id}", response_model=HabitRead, summary="Update a habit")
def update_habit(
    habit_id: int,
    payload: HabitUpdate,
    service: Annotated[HabitService, Depends(get_habit_service)],
) -> HabitRead:
    return service.update_habit(habit_id, payload)


@router.post("/{habit_id}/pause", response_model=HabitRead, summary="Pause a habit")
def pause_habit(
    habit_id: int,
    service: Annotated[HabitService, Depends(get_habit_service)],
) -> HabitRead:
    return service.pause(habit_id)


@router.post("/{habit_id}/resume", response_model=HabitRead, summary="Resume a paused habit")
def resume_habit(
    habit_id: int,
    service: Annotated[HabitService, Depends(get_habit_service)],
) -> HabitRead:
    return service.resume(habit_id)


@router.delete(
    "/{habit_id}",
    response_model=HabitDeleteResponse,
    summary="Delete a habit and its check-ins",
)
def delete_habit(
    habit_id: int,
    service: Annotated[HabitService, Depends(get_habit_service)],
) -> HabitDeleteResponse:
    return service.delete_habit(habit_id)


@router.get(
    "/{habit_id}/check-ins",
    response_model=list[CheckInRead],
    summary="List check-ins for a habit",
)
def list_check_ins(
    habit_id: int,
    service: Annotated[HabitService, Depends(get_habit_service)],
    from_date: Annotated[date | None, Query()] = None,
    to_date: Annotated[date | None, Query()] = None,
) -> list[CheckInRead]:
    return service.list_check_ins(habit_id, from_date=from_date, to_date=to_date)


@router.post(
    "/{habit_id}/check-ins",
    response_model=CheckInRead,
    status_code=status.HTTP_201_CREATED,
    summary="Log a check-in",
    description="One check-in per habit per calendar day. Paused habits return **409**.",
)
def create_check_in(
    habit_id: int,
    service: Annotated[HabitService, Depends(get_habit_service)],
    payload: Annotated[CheckInCreate, Body(openapi_examples=_CHECK_IN_EXAMPLES)],
) -> CheckInRead:
    return service.check_in(habit_id, payload)


@router.delete(
    "/{habit_id}/check-ins/{check_in_id}",
    response_model=CheckInDeleteResponse,
    summary="Remove a check-in",
)
def delete_check_in(
    habit_id: int,
    check_in_id: int,
    service: Annotated[HabitService, Depends(get_habit_service)],
) -> CheckInDeleteResponse:
    return service.delete_check_in(habit_id, check_in_id)


@router.get(
    "/{habit_id}/stats",
    response_model=HabitStats,
    summary="Streak and weekly progress",
    description="Pass `week_of` (any date in the week) to evaluate weekly targets.",
)
def habit_stats(
    habit_id: int,
    service: Annotated[HabitService, Depends(get_habit_service)],
    week_of: Annotated[date | None, Query()] = None,
) -> HabitStats:
    return service.stats(habit_id, week_of=week_of)
