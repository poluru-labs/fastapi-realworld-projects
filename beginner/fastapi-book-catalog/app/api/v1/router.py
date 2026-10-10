from fastapi import APIRouter

from app.api.v1.endpoints import books, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(books.router, prefix="/books", tags=["books"])
