from datetime import date

from app.schemas.habit import CheckInCreate, CheckInRead, HabitCreate, HabitRead, HabitUpdate

_SEED_HABITS: dict[int, HabitRead] = {
    1: HabitRead(
        id=1,
        name="Morning run",
        category="Health",
        target_days_per_week=4,
        note="20 minutes outside.",
        paused=False,
    ),
    2: HabitRead(
        id=2,
        name="Read 20 minutes",
        category="Learning",
        target_days_per_week=7,
        note="Any book or article.",
        paused=False,
    ),
    3: HabitRead(
        id=3,
        name="Evening meditation",
        category="Health",
        target_days_per_week=5,
        note="Paused while traveling.",
        paused=True,
    ),
}

_SEED_CHECK_INS: dict[int, CheckInRead] = {
    1: CheckInRead(id=1, habit_id=1, checked_on=date.fromisoformat("2026-10-12"), note=""),
    2: CheckInRead(id=2, habit_id=1, checked_on=date.fromisoformat("2026-10-13"), note=""),
    3: CheckInRead(id=3, habit_id=1, checked_on=date.fromisoformat("2026-10-14"), note="Park loop"),
    4: CheckInRead(
        id=4,
        habit_id=2,
        checked_on=date.fromisoformat("2026-10-14"),
        note="FastAPI docs",
    ),
}


class HabitRepository:
    """In-memory habits and check-ins. Restarting the process restores seed data."""

    def __init__(self) -> None:
        self._habits = dict(_SEED_HABITS)
        self._check_ins = dict(_SEED_CHECK_INS)
        self._next_habit_id = max(self._habits.keys(), default=0) + 1
        self._next_check_in_id = max(self._check_ins.keys(), default=0) + 1

    def list_habits(
        self,
        *,
        category: str | None,
        search: str | None,
        paused: bool | None,
    ) -> list[HabitRead]:
        rows = list(self._habits.values())
        if category is not None:
            needle = category.strip().casefold()
            if needle:
                rows = [row for row in rows if row.category.casefold() == needle]
        if paused is not None:
            rows = [row for row in rows if row.paused is paused]
        if search is not None:
            needle = search.strip().casefold()
            if needle:
                rows = [
                    row
                    for row in rows
                    if needle in row.name.casefold()
                    or needle in row.note.casefold()
                    or needle in row.category.casefold()
                ]
        return sorted(rows, key=lambda row: (row.paused, row.name.casefold(), row.id))

    def list_categories(self) -> list[str]:
        return sorted({row.category for row in self._habits.values()}, key=str.casefold)

    def get_habit(self, habit_id: int) -> HabitRead | None:
        return self._habits.get(habit_id)

    def create_habit(self, payload: HabitCreate) -> HabitRead:
        row = HabitRead(id=self._next_habit_id, paused=False, **payload.model_dump())
        self._habits[row.id] = row
        self._next_habit_id += 1
        return row

    def update_habit(self, habit_id: int, payload: HabitUpdate) -> HabitRead | None:
        existing = self._habits.get(habit_id)
        if existing is None:
            return None
        data = existing.model_dump()
        data.update(payload.model_dump(exclude_unset=True))
        row = HabitRead(**data)
        self._habits[habit_id] = row
        return row

    def set_paused(self, habit_id: int, paused: bool) -> HabitRead | None:
        existing = self._habits.get(habit_id)
        if existing is None:
            return None
        row = existing.model_copy(update={"paused": paused})
        self._habits[habit_id] = row
        return row

    def delete_habit(self, habit_id: int) -> HabitRead | None:
        removed = self._habits.pop(habit_id, None)
        if removed is not None:
            self._check_ins = {
                cid: row for cid, row in self._check_ins.items() if row.habit_id != habit_id
            }
        return removed

    def list_check_ins(
        self,
        habit_id: int,
        *,
        from_date: date | None,
        to_date: date | None,
    ) -> list[CheckInRead]:
        rows = [row for row in self._check_ins.values() if row.habit_id == habit_id]
        if from_date is not None:
            rows = [row for row in rows if row.checked_on >= from_date]
        if to_date is not None:
            rows = [row for row in rows if row.checked_on <= to_date]
        return sorted(rows, key=lambda row: (row.checked_on, row.id), reverse=True)

    def check_in_exists(self, habit_id: int, checked_on: date) -> bool:
        return any(
            row.habit_id == habit_id and row.checked_on == checked_on
            for row in self._check_ins.values()
        )

    def add_check_in(self, habit_id: int, payload: CheckInCreate) -> CheckInRead:
        row = CheckInRead(
            id=self._next_check_in_id,
            habit_id=habit_id,
            checked_on=payload.checked_on,
            note=payload.note,
        )
        self._check_ins[row.id] = row
        self._next_check_in_id += 1
        return row

    def get_check_in(self, check_in_id: int) -> CheckInRead | None:
        return self._check_ins.get(check_in_id)

    def delete_check_in(self, check_in_id: int) -> CheckInRead | None:
        return self._check_ins.pop(check_in_id, None)
