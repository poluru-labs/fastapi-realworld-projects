from fastapi import APIRouter

from app.api.v1.endpoints import auth, documents, folders, health, library, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(library.router, prefix="/library", tags=["library"])
api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
api_router.include_router(
    documents.router,
    prefix="/folders/{folder_slug}/documents",
    tags=["documents"],
)
