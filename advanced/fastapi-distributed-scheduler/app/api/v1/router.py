from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, runs, schedules, workers

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(schedules.router)
api_router.include_router(runs.router)
api_router.include_router(workers.router)
