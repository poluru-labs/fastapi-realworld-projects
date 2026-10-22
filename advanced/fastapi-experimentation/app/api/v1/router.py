from fastapi import APIRouter

from app.api.v1.endpoints import events, experiments, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
api_router.include_router(
    events.router,
    prefix="/experiments/{experiment_key}/events",
    tags=["events"],
)
