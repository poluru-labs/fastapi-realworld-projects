from fastapi import APIRouter

from app.api.v1.endpoints import health, polls

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(polls.router, prefix="/polls", tags=["polls"])
