from fastapi import APIRouter

from app.api.v1.endpoints import files, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
