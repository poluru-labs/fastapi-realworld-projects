from fastapi import APIRouter

from app.api.v1.endpoints import habits, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(habits.router, prefix="/habits", tags=["habits"])
