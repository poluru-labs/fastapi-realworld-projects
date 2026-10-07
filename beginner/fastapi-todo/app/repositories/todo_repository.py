from app.schemas.todo import Priority, TodoCreate, TodoRead, TodoUpdate

_SEED: dict[int, TodoRead] = {
    1: TodoRead(
        id=1,
        title="Buy groceries",
        notes="Milk and bread",
        priority=Priority.MEDIUM,
        completed=False,
    ),
    2: TodoRead(
        id=2,
        title="Read the FastAPI tutorial",
        notes="",
        priority=Priority.HIGH,
        completed=False,
    ),
    3: TodoRead(
        id=3,
        title="Set up the project",
        notes="venv and uvicorn",
        priority=Priority.LOW,
        completed=True,
    ),
}


class TodoRepository:
    """In-memory todo list. A new process starts from the seed data again."""

    def __init__(self) -> None:
        self._todos = dict(_SEED)
        self._next_id = max(self._todos.keys(), default=0) + 1

    def list_todos(
        self,
        *,
        completed: bool | None = None,
        priority: Priority | None = None,
    ) -> list[TodoRead]:
        items = list(self._todos.values())
        if completed is not None:
            items = [todo for todo in items if todo.completed is completed]
        if priority is not None:
            items = [todo for todo in items if todo.priority is priority]
        return sorted(items, key=lambda todo: todo.id)

    def get(self, todo_id: int) -> TodoRead | None:
        return self._todos.get(todo_id)

    def create(self, payload: TodoCreate) -> TodoRead:
        todo = TodoRead(id=self._next_id, **payload.model_dump())
        self._todos[self._next_id] = todo
        self._next_id += 1
        return todo

    def update(self, todo_id: int, payload: TodoUpdate) -> TodoRead | None:
        existing = self._todos.get(todo_id)
        if existing is None:
            return None
        data = existing.model_dump()
        data.update(payload.model_dump(exclude_unset=True))
        todo = TodoRead(**data)
        self._todos[todo_id] = todo
        return todo

    def set_completed(self, todo_id: int, completed: bool) -> TodoRead | None:
        existing = self._todos.get(todo_id)
        if existing is None:
            return None
        todo = existing.model_copy(update={"completed": completed})
        self._todos[todo_id] = todo
        return todo

    def delete(self, todo_id: int) -> TodoRead | None:
        return self._todos.pop(todo_id, None)
