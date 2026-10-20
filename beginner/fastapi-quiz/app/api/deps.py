from app.repositories.quiz_repository import get_quiz_repository
from app.services.quiz_service import QuizService


def get_quiz_service() -> QuizService:
    return QuizService(get_quiz_repository())
