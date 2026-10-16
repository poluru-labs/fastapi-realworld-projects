from app.repositories.bookmark_repository import get_bookmark_repository
from app.services.bookmark_service import BookmarkService


def get_bookmark_service() -> BookmarkService:
    return BookmarkService(get_bookmark_repository())
