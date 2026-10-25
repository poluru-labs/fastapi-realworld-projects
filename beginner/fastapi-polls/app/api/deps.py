from functools import lru_cache

from app.repositories.poll_repository import PollRepository
from app.services.poll_service import PollService


@lru_cache
def get_poll_repository() -> PollRepository:
    return PollRepository()


def get_poll_service() -> PollService:
    return PollService(get_poll_repository())
