from fastapi import APIRouter

from app.api.v1.endpoints import health, runs, workflows

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(workflows.router, prefix="/agent-workflows", tags=["workflows"])
api_router.include_router(runs.router, prefix="/agent-runs", tags=["runs"])
