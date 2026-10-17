from fastapi import APIRouter

from app.api.v1.endpoints import entries, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(entries.router, prefix="/entries", tags=["entries"])
