from dataclasses import dataclass
from datetime import UTC, datetime

from app.schemas.task import TaskStatus


@dataclass
class TaskRecord:
    id: int
    team_id: int
    title: str
    description: str
    status: TaskStatus
    assignee_id: int | None
    created_by: int
    created_at: datetime


class TaskRepository:
    """In-memory tasks keyed by id. Reset when the process restarts."""

    def __init__(self) -> None:
        self._tasks: dict[int, TaskRecord] = {
            1: TaskRecord(
                id=1,
                team_id=1,
                title="Write the API guide",
                description="Document auth, teams, and the task status flow.",
                status=TaskStatus.TODO,
                assignee_id=1,
                created_by=1,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        }
        self._next_id = 2

    def list_for_team(
        self,
        team_id: int,
        *,
        status: TaskStatus | None = None,
        assignee_id: int | None = None,
    ) -> list[TaskRecord]:
        rows = [task for task in self._tasks.values() if task.team_id == team_id]
        if status is not None:
            rows = [task for task in rows if task.status is status]
        if assignee_id is not None:
            rows = [task for task in rows if task.assignee_id == assignee_id]
        return sorted(rows, key=lambda task: task.id)

    def get(self, team_id: int, task_id: int) -> TaskRecord | None:
        task = self._tasks.get(task_id)
        if task is None or task.team_id != team_id:
            return None
        return task

    def add(self, record: TaskRecord) -> TaskRecord:
        self._tasks[record.id] = record
        return record

    def allocate_id(self) -> int:
        task_id = self._next_id
        self._next_id += 1
        return task_id

    def save(self, record: TaskRecord) -> None:
        self._tasks[record.id] = record

    def delete(self, task_id: int) -> None:
        self._tasks.pop(task_id, None)

    def delete_for_team(self, team_id: int) -> None:
        doomed = [task_id for task_id, task in self._tasks.items() if task.team_id == team_id]
        for task_id in doomed:
            del self._tasks[task_id]

    def clear_assignee(self, team_id: int, user_id: int) -> None:
        for task in self._tasks.values():
            if task.team_id == team_id and task.assignee_id == user_id:
                task.assignee_id = None
