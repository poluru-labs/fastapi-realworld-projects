from fastapi import APIRouter

from app.api.v1.endpoints import analyze, health, options, transform

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(options.router, prefix="/options", tags=["options"])
api_router.include_router(analyze.router, prefix="/analyze", tags=["analyze"])
api_router.include_router(transform.router, prefix="/transform", tags=["transform"])
