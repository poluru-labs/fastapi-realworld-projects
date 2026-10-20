from fastapi import APIRouter

from app.api.v1.endpoints import health, questions, quizzes

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(quizzes.router, prefix="/quizzes", tags=["quizzes"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
