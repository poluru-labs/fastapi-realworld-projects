from datetime import date, timedelta

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.habit_repository import HabitRepository
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


def _current_streak(dates: list[date]) -> int:
    if not dates:
        return 0
    unique = sorted(set(dates), reverse=True)
    streak = 1
    for index in range(1, len(unique)):
        if (unique[index - 1] - unique[index]).days == 1:
            streak += 1
        else:
            break
    return streak


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


class HabitService:
    def __init__(self, repository: HabitRepository) -> None:
        self._repo = repository

    def list_habits(
        self,
        *,
        category: str | None = None,
        search: str | None = None,
        paused: bool | None = None,
    ) -> list[HabitRead]:
        return self._repo.list_habits(category=category, search=search, paused=paused)

    def list_categories(self) -> list[str]:
        return self._repo.list_categories()

    def get_habit(self, habit_id: int) -> HabitRead:
        row = self._repo.get_habit(habit_id)
        if row is None:
            raise NotFoundError("Habit", habit_id)
        return row

    def create_habit(self, payload: HabitCreate) -> HabitRead:
        return self._repo.create_habit(payload)

    def update_habit(self, habit_id: int, payload: HabitUpdate) -> HabitRead:
        row = self._repo.update_habit(habit_id, payload)
        if row is None:
            raise NotFoundError("Habit", habit_id)
        return row

    def pause(self, habit_id: int) -> HabitRead:
        return self._set_paused(habit_id, True)

    def resume(self, habit_id: int) -> HabitRead:
        return self._set_paused(habit_id, False)

    def delete_habit(self, habit_id: int) -> HabitDeleteResponse:
        row = self._repo.delete_habit(habit_id)
        if row is None:
            raise NotFoundError("Habit", habit_id)
        return HabitDeleteResponse(habit=row)

    def list_check_ins(
        self,
        habit_id: int,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[CheckInRead]:
        self._require_habit(habit_id)
        return self._repo.list_check_ins(habit_id, from_date=from_date, to_date=to_date)

    def check_in(self, habit_id: int, payload: CheckInCreate) -> CheckInRead:
        habit = self._require_habit(habit_id)
        if habit.paused:
            raise ConflictError("Cannot check in while the habit is paused")
        if self._repo.check_in_exists(habit_id, payload.checked_on):
            raise ConflictError(f"You already checked in on {payload.checked_on.isoformat()}")
        return self._repo.add_check_in(habit_id, payload)

    def delete_check_in(self, habit_id: int, check_in_id: int) -> CheckInDeleteResponse:
        self._require_habit(habit_id)
        row = self._repo.get_check_in(check_in_id)
        if row is None or row.habit_id != habit_id:
            raise NotFoundError("CheckIn", check_in_id)
        removed = self._repo.delete_check_in(check_in_id)
        assert removed is not None
        return CheckInDeleteResponse(check_in=removed)

    def stats(self, habit_id: int, *, week_of: date | None = None) -> HabitStats:
        habit = self._require_habit(habit_id)
        rows = self._repo.list_check_ins(habit_id, from_date=None, to_date=None)
        dates = [row.checked_on for row in rows]
        anchor = week_of or date.today()
        start = _week_start(anchor)
        end = start + timedelta(days=6)
        this_week = sum(1 for day in dates if start <= day <= end)
        return HabitStats(
            habit_id=habit.id,
            current_streak=_current_streak(dates),
            total_check_ins=len(rows),
            check_ins_this_week=this_week,
            on_target_this_week=this_week >= habit.target_days_per_week,
        )

    def _set_paused(self, habit_id: int, paused: bool) -> HabitRead:
        row = self._repo.set_paused(habit_id, paused)
        if row is None:
            raise NotFoundError("Habit", habit_id)
        return row

    def _require_habit(self, habit_id: int) -> HabitRead:
        row = self._repo.get_habit(habit_id)
        if row is None:
            raise NotFoundError("Habit", habit_id)
        return row
