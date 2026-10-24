from fastapi import APIRouter

from app.api.v1.endpoints import assets, auth, health, jobs, presets, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(presets.router, prefix="/presets", tags=["presets"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
