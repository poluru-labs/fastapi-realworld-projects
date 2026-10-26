from fastapi import APIRouter

from app.api.v1.endpoints import health, links, redirect

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(links.router, prefix="/links", tags=["links"])
api_router.include_router(redirect.router, prefix="/r", tags=["redirect"])
