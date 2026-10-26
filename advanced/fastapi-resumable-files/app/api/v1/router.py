from fastapi import APIRouter

from app.api.v1.endpoints import health, parts, uploads

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(
    parts.router,
    prefix="/uploads/{upload_key}/parts",
    tags=["parts"],
)
