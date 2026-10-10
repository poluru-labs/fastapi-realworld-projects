from fastapi import APIRouter

from app.api.v1.endpoints import auth, events, health, registrations, tags, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(registrations.router, prefix="/registrations", tags=["registrations"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
