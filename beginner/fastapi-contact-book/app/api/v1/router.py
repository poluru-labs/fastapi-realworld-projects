from fastapi import APIRouter

from app.api.v1.endpoints import contacts, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
