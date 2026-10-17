from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, messages, relays, rooms

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(rooms.router)
api_router.include_router(messages.router)
api_router.include_router(relays.router)
