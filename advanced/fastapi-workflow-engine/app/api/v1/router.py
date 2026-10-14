from fastapi import APIRouter

from app.api.v1.endpoints import auth, definitions, health, instances

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(definitions.router)
api_router.include_router(instances.router)
