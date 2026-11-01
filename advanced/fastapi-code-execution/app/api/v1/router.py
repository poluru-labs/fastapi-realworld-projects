from fastapi import APIRouter

from app.api.v1.endpoints import health, policy, runs

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(policy.router, prefix="/execution/policy", tags=["policy"])
api_router.include_router(runs.router, prefix="/execution/runs", tags=["runs"])
