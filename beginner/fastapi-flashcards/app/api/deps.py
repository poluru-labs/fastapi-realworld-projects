from app.repositories.flashcard_repository import get_flashcard_repository
from app.services.flashcard_service import FlashcardService


def get_flashcard_service() -> FlashcardService:
    return FlashcardService(get_flashcard_repository())


# Re-export for tests that clear the cache.
__all__ = ["get_flashcard_repository", "get_flashcard_service"]
