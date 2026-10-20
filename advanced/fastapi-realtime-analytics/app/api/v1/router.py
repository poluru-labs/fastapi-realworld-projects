from fastapi import APIRouter

from app.api.v1.endpoints import alerts, events, health, metrics, streams

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(streams.router, prefix="/streams", tags=["streams"])
api_router.include_router(
    events.router,
    prefix="/streams/{stream_key}/events",
    tags=["events"],
)
api_router.include_router(
    metrics.router,
    prefix="/streams/{stream_key}/metrics",
    tags=["metrics"],
)
api_router.include_router(
    alerts.router,
    prefix="/streams/{stream_key}/alerts",
    tags=["alerts"],
)
