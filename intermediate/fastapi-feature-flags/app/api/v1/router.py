from fastapi import APIRouter

from app.api.v1.endpoints import auth, flags, health, runtime, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(flags.router, prefix="/flags", tags=["flags"])
api_router.include_router(runtime.router, prefix="/runtime", tags=["runtime"])
