from fastapi import APIRouter

from app.api.v1.endpoints import alerts, devices, health, metrics, telemetry

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(
    telemetry.router,
    prefix="/devices/{device_key}/telemetry",
    tags=["telemetry"],
)
api_router.include_router(
    metrics.router,
    prefix="/devices/{device_key}/metrics",
    tags=["metrics"],
)
api_router.include_router(
    alerts.router,
    prefix="/devices/{device_key}/alerts",
    tags=["alerts"],
)
