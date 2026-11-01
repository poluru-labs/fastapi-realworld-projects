from fastapi import APIRouter

from app.api.v1.endpoints import auth, clients, health, oauth

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(clients.router, prefix="/oauth/clients", tags=["clients"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
