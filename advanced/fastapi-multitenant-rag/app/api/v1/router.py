from fastapi import APIRouter

from app.api.v1.endpoints import auth, collections, health, tenants

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])
