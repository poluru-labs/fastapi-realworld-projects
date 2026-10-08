from functools import lru_cache

from app.repositories.note_repository import NoteRepository
from app.services.note_service import NoteService


@lru_cache
def get_note_repository() -> NoteRepository:
    return NoteRepository()


def get_note_service() -> NoteService:
    return NoteService(get_note_repository())
