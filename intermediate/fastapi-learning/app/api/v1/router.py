from fastapi import APIRouter

from app.api.v1.endpoints import auth, courses, enrollments, health, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(courses.router, tags=["courses"])
api_router.include_router(enrollments.router)
