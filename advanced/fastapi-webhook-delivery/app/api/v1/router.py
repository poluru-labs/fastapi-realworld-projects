from fastapi import APIRouter

from app.api.v1.endpoints import auth, capture, deliveries, endpoints, events, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(endpoints.router)
api_router.include_router(events.router)
api_router.include_router(deliveries.router)
api_router.include_router(capture.router)
