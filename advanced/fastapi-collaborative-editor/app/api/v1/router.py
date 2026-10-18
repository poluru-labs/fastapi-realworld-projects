from fastapi import APIRouter

from app.api.v1.endpoints import auth, documents, edits, health, sync

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(edits.router)
api_router.include_router(sync.router)
