from fastapi import APIRouter

from app.api.v1.endpoints import events, geofences, health, locations, trackers

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(trackers.router, prefix="/trackers", tags=["trackers"])
api_router.include_router(
    locations.router,
    prefix="/trackers/{tracker_key}/locations",
    tags=["locations"],
)
api_router.include_router(geofences.router, prefix="/geofences", tags=["geofences"])
api_router.include_router(
    events.router,
    prefix="/trackers/{tracker_key}/geofence-events",
    tags=["geofence-events"],
)
