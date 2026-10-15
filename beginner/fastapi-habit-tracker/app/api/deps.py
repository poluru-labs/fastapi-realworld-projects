from functools import lru_cache

from app.repositories.habit_repository import HabitRepository
from app.services.habit_service import HabitService


@lru_cache
def get_habit_repository() -> HabitRepository:
    return HabitRepository()


def get_habit_service() -> HabitService:
    return HabitService(get_habit_repository())
