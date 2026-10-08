from fastapi import APIRouter

from app.api.v1.endpoints import health, notes

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
