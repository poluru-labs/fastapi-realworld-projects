from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, projects, tenants, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tenants.router)
api_router.include_router(projects.router)
