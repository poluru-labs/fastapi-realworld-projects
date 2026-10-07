from functools import lru_cache

from app.repositories.todo_repository import TodoRepository
from app.services.todo_service import TodoService


@lru_cache
def get_todo_repository() -> TodoRepository:
    return TodoRepository()


def get_todo_service() -> TodoService:
    return TodoService(get_todo_repository())
