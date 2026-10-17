from fastapi import APIRouter

from app.api.v1.endpoints import auth, categories, health, replies, tickets, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(
    replies.router,
    prefix="/tickets/{slug}/replies",
    tags=["replies"],
)
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
