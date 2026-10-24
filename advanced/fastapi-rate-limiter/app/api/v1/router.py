from fastapi import APIRouter

from app.api.v1.endpoints import clients, health, policies, quota

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(policies.router, prefix="/policies", tags=["policies"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(quota.router, prefix="/quota", tags=["quota"])
