from fastapi import APIRouter

from app.api.v1.endpoints import appointments, auth, health, providers, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
