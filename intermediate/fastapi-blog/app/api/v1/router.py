from fastapi import APIRouter

from app.api.v1.endpoints import auth, comments, health, posts, tags, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(comments.router, prefix="/posts/{slug}/comments", tags=["comments"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
