from fastapi import APIRouter

from app.api.v1.endpoints import convert, health, units

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(units.router, prefix="/units", tags=["units"])
api_router.include_router(convert.router, prefix="/convert", tags=["convert"])
