from app.core.exceptions import NotFoundError
from app.repositories.todo_repository import TodoRepository
from app.schemas.todo import Priority, TodoCreate, TodoRead, TodoUpdate


class TodoService:
    def __init__(self, repository: TodoRepository) -> None:
        self._repo = repository

    def list_todos(
        self,
        *,
        completed: bool | None = None,
        priority: Priority | None = None,
    ) -> list[TodoRead]:
        return self._repo.list_todos(completed=completed, priority=priority)

    def get_todo(self, todo_id: int) -> TodoRead:
        todo = self._repo.get(todo_id)
        if todo is None:
            raise NotFoundError("Todo", todo_id)
        return todo

    def create_todo(self, payload: TodoCreate) -> TodoRead:
        return self._repo.create(payload)

    def update_todo(self, todo_id: int, payload: TodoUpdate) -> TodoRead:
        todo = self._repo.update(todo_id, payload)
        if todo is None:
            raise NotFoundError("Todo", todo_id)
        return todo

    def complete_todo(self, todo_id: int) -> TodoRead:
        todo = self._repo.set_completed(todo_id, True)
        if todo is None:
            raise NotFoundError("Todo", todo_id)
        return todo

    def reopen_todo(self, todo_id: int) -> TodoRead:
        todo = self._repo.set_completed(todo_id, False)
        if todo is None:
            raise NotFoundError("Todo", todo_id)
        return todo

    def delete_todo(self, todo_id: int) -> TodoRead:
        todo = self._repo.delete(todo_id)
        if todo is None:
            raise NotFoundError("Todo", todo_id)
        return todo
