from fastapi import APIRouter

from app.api.v1.endpoints import cards, decks, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(decks.router, prefix="/decks", tags=["decks"])
api_router.include_router(cards.router, prefix="/cards", tags=["cards"])
