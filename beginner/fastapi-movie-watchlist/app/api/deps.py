from functools import lru_cache

from app.repositories.movie_repository import MovieRepository
from app.services.movie_service import MovieService


@lru_cache
def get_movie_repository() -> MovieRepository:
    return MovieRepository()


def get_movie_service() -> MovieService:
    return MovieService(get_movie_repository())
