from functools import lru_cache

from app.repositories.book_repository import BookRepository
from app.services.book_service import BookService


@lru_cache
def get_book_repository() -> BookRepository:
    return BookRepository()


def get_book_service() -> BookService:
    return BookService(get_book_repository())
