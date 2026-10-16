from fastapi import APIRouter

from app.api.v1.endpoints import (
    applications,
    auth,
    health,
    jobs,
    my_applications,
    skills,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(
    applications.router,
    prefix="/jobs/{slug}/applications",
    tags=["applications"],
)
api_router.include_router(
    my_applications.router,
    prefix="/applications",
    tags=["applications"],
)
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
