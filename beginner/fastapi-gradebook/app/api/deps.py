from app.repositories.gradebook_repository import get_gradebook_repository
from app.services.gradebook_service import GradebookService


def get_gradebook_service() -> GradebookService:
    return GradebookService(get_gradebook_repository())
