from fastapi import APIRouter

from app.api.v1.endpoints import auth, deliveries, endpoints, health, hooks, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(endpoints.router, prefix="/endpoints", tags=["endpoints"])
api_router.include_router(deliveries.router, prefix="/deliveries", tags=["deliveries"])
api_router.include_router(hooks.router, prefix="/hooks", tags=["hooks"])
