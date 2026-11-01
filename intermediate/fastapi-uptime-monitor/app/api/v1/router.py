from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, monitors, status, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(monitors.router, prefix="/monitors", tags=["monitors"])
api_router.include_router(status.router, prefix="/status", tags=["status"])
