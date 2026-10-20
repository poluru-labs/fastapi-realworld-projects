from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, messages, rooms, users, ws

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
api_router.include_router(
    messages.router,
    prefix="/rooms/{slug}/messages",
    tags=["messages"],
)
api_router.include_router(ws.router, prefix="/ws", tags=["realtime"])
