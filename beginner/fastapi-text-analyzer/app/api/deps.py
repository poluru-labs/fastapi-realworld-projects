from functools import lru_cache

from app.repositories.analyzer_repository import AnalyzerRepository
from app.services.text_service import TextService


@lru_cache
def get_analyzer_repository() -> AnalyzerRepository:
    return AnalyzerRepository()


def get_text_service() -> TextService:
    return TextService(get_analyzer_repository())
